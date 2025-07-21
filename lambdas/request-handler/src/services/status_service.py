import logging
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, Optional

import boto3
from botocore.exceptions import ClientError

from app.config import settings

logger = logging.getLogger(__name__)


class ProcessingStatus(Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    DETECTING = "detecting"
    ANALYZING_MATURATION = "analyzing_maturation"
    UPLOADING_RESULTS = "uploading_results"
    COMPLETED = "completed"
    ERROR = "error"
    TIMEOUT = "timeout"


class StatusService:
    def __init__(self):
        self.dynamodb = boto3.resource("dynamodb", region_name=settings.AWS_REGION)
        self.table = self.dynamodb.Table(settings.DYNAMODB_TABLE_NAME)

    async def create_initial_status(
        self, request_id: str, user_id: str, image_url: str, metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        try:
            now = datetime.now(timezone.utc)
            ttl = int((now + timedelta(days=settings.DYNAMODB_TTL_DAYS)).timestamp())

            status_item = {
                "pk": f"STATUS#{request_id}",
                "sk": "INFO",
                "request_id": request_id,
                "user_id": user_id,
                "status": ProcessingStatus.QUEUED.value,
                "progress": 0.0,
                "image_url": image_url,
                "metadata": metadata,
                "created_at": now.isoformat(),
                "updated_at": now.isoformat(),
                "ttl": ttl,
                "entity_type": "PROCESSING_STATUS",
            }

            self.table.put_item(Item=status_item)

            logger.info(f"Status inicial criado para solicitação: {request_id}")

            return status_item

        except ClientError as e:
            logger.exception(f"Erro ao criar entrada de status: {e}")
            raise Exception(f"Falha ao criar entrada de status: {str(e)}")

    async def get_status(self, request_id: str) -> Optional[Dict[str, Any]]:
        try:
            response = self.table.get_item(Key={"pk": f"STATUS#{request_id}", "sk": "INFO"})

            item = response.get("Item")
            if not item:
                logger.warning(f"Status não encontrado para solicitação: {request_id}")
                return None

            created_at = datetime.fromisoformat(item["created_at"])
            elapsed_seconds = (datetime.now(timezone.utc) - created_at).total_seconds()

            item["elapsed_seconds"] = elapsed_seconds
            item["is_timeout"] = elapsed_seconds > settings.PROCESSING_TIMEOUT_SECONDS

            return item

        except ClientError as e:
            logger.exception(f"Erro ao obter status: {e}")
            return None

    async def update_status(
        self,
        request_id: str,
        status: ProcessingStatus,
        progress: Optional[float] = None,
        additional_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        try:
            update_expression = "SET #status = :status, updated_at = :updated_at"
            expression_values = {":status": status.value, ":updated_at": datetime.now(timezone.utc).isoformat()}
            expression_names = {"#status": "status"}

            if progress is not None:
                update_expression += ", progress = :progress"
                expression_values[":progress"] = progress

            if additional_data:
                for key, value in additional_data.items():
                    safe_key = f"#{key}"
                    update_expression += f", {safe_key} = :{key}"
                    expression_values[f":{key}"] = value
                    expression_names[safe_key] = key

            response = self.table.update_item(
                Key={"pk": f"STATUS#{request_id}", "sk": "INFO"},
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_values,
                ExpressionAttributeNames=expression_names,
                ReturnValues="ALL_NEW",
            )

            logger.info(f"Status atualizado para solicitação {request_id}: {status.value}")

            return response.get("Attributes", {})

        except ClientError as e:
            logger.exception(f"Erro ao atualizar status: {e}")
            raise Exception(f"Falha ao atualizar status: {str(e)}")

    async def mark_as_error(
        self, request_id: str, error_message: str, error_code: Optional[str] = None
    ) -> Dict[str, Any]:
        additional_data = {"error_message": error_message, "error_at": datetime.now(timezone.utc).isoformat()}

        if error_code:
            additional_data["error_code"] = error_code

        return await self.update_status(
            request_id=request_id, status=ProcessingStatus.ERROR, progress=1.0, additional_data=additional_data
        )

    async def get_user_requests(
        self, user_id: str, limit: int = 10, status_filter: Optional[ProcessingStatus] = None
    ) -> list[Dict[str, Any]]:
        try:
            query_params = {
                "IndexName": "UserIdIndex",
                "KeyConditionExpression": "user_id = :user_id",
                "ExpressionAttributeValues": {":user_id": user_id},
                "ScanIndexForward": False,
                "Limit": limit,
            }

            if status_filter:
                query_params["FilterExpression"] = "#status = :status"
                query_params["ExpressionAttributeNames"] = {"#status": "status"}
                query_params["ExpressionAttributeValues"][":status"] = status_filter.value

            response = self.table.query(**query_params)

            items = response.get("Items", [])

            status_items = [item for item in items if item.get("entity_type") == "PROCESSING_STATUS"]

            return status_items

        except ClientError as e:
            logger.exception(f"Erro ao obter solicitações do usuário: {e}")
            return []

    async def cleanup_old_statuses(self, days_old: int = 7) -> int:
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_old)

            response = self.table.scan(
                FilterExpression="entity_type = :type AND created_at < :cutoff",
                ExpressionAttributeValues={":type": "PROCESSING_STATUS", ":cutoff": cutoff_date.isoformat()},
            )

            items = response.get("Items", [])
            deleted_count = 0

            for item in items:
                try:
                    self.table.delete_item(Key={"pk": item["pk"], "sk": item["sk"]})
                    deleted_count += 1
                except Exception as e:
                    logger.warning(f"Falha ao excluir item: {e}")

            logger.info(f"Limpeza de {deleted_count} entradas de status antigas concluída")
            return deleted_count

        except ClientError as e:
            logger.exception(f"Erro ao limpar status antigos: {e}")
            return 0
