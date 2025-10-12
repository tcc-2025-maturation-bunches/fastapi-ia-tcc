import logging
from datetime import datetime, timezone
from typing import Any, Dict

from fruit_detection_shared.infra.external import DynamoClient

from src.app.config import settings

logger = logging.getLogger(__name__)


class DynamoRepository:
    def __init__(self, dynamo_client: DynamoClient = None):
        self.dynamo_client = dynamo_client or DynamoClient(table_name=settings.DYNAMODB_TABLE_NAME)

    async def save_request_summary(self, item: Dict[str, Any]) -> Dict[str, Any]:
        try:
            logger.info(f"Salvando resumo da requisição {item.get('request_id')}")
            return await self.dynamo_client.put_item(item)
        except Exception as e:
            logger.exception(f"Erro ao salvar resumo da requisição: {e}")
            raise

    async def update_processing_status(self, request_id: str, status_data: Dict[str, Any]) -> None:
        try:
            key = {"pk": f"STATUS#{request_id}", "sk": "INFO"}

            update_expressions = []
            expression_values = {}
            expression_names = {}

            for field, value in status_data.items():
                if field == "status":
                    update_expressions.append("#status = :status")
                    expression_names["#status"] = "status"
                    expression_values[":status"] = value
                else:
                    update_expressions.append(f"{field} = :{field}")
                    expression_values[f":{field}"] = value

            update_expression = "SET " + ", ".join(update_expressions)

            await self.dynamo_client.update_item(
                key=key,
                update_expression=update_expression,
                expression_values=expression_values,
                expression_names=expression_names if expression_names else None,
            )

            logger.debug(f"Status de processamento atualizado para {request_id}")

        except Exception as e:
            logger.warning(f"Erro ao atualizar status de processamento para {request_id}: {e}")

    async def get_processing_status(self, request_id: str) -> Dict[str, Any]:
        try:
            key = {"pk": f"STATUS#{request_id}", "sk": "INFO"}
            return await self.dynamo_client.get_item(key)
        except Exception as e:
            logger.exception(f"Erro ao recuperar status de processamento: {e}")
            return {}

    async def mark_as_completed(self, request_id: str, result_data: Dict[str, Any]) -> None:
        try:
            status_data = {
                "status": "completed",
                "progress": 1.0,
                "completed_at": datetime.now(timezone.utc).isoformat(),
                **result_data,
            }
            await self.update_processing_status(request_id, status_data)
        except Exception as e:
            logger.exception(f"Erro ao marcar como concluído: {e}")

    async def mark_as_failed(self, request_id: str, error: str, error_code: str = None) -> None:
        try:
            status_data = {
                "status": "error",
                "progress": 1.0,
                "error": error,
                "error_code": error_code or "UNKNOWN_ERROR",
                "failed_at": datetime.now(timezone.utc).isoformat(),
            }
            await self.update_processing_status(request_id, status_data)
        except Exception as e:
            logger.exception(f"Erro ao marcar como falho: {e}")
