import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.app.config import settings
from src.shared.domain.entities.combined_result import CombinedResult
from src.shared.domain.entities.image import Image
from src.shared.infra.external.dynamo.dynamo_client import DynamoClient

logger = logging.getLogger(__name__)


class DynamoRepository:

    def __init__(self, dynamo_client: Optional[DynamoClient] = None):
        self.results_client = dynamo_client or DynamoClient(table_name=settings.DYNAMODB_TABLE_NAME)

        logger.info(f"Inicializando DynamoRepository para tabela de resultados: {settings.DYNAMODB_TABLE_NAME}")

    async def save_image_metadata(self, image: Image) -> Dict[str, Any]:
        try:
            item = image.to_dict()
            item["pk"] = f"IMG#{image.image_id}"
            item["sk"] = f"META#{image.image_id}"
            item["entity_type"] = "IMAGE"
            item["user_id"] = image.user_id
            item["createdAt"] = image.upload_timestamp.isoformat()
            item["updatedAt"] = image.upload_timestamp.isoformat()

            logger.info(f"Salvando metadados da imagem {image.image_id} na tabela de resultados")
            return await self.results_client.put_item(item)

        except Exception as e:
            logger.exception(f"Erro ao salvar metadados da imagem na tabela de resultados: {e}")
            raise

    async def save_combined_result(self, user_id: str, combined_result: CombinedResult) -> Dict[str, Any]:
        try:
            item = combined_result.to_contract_dict()

            now = combined_result.processing_metadata.timestamp if combined_result.processing_metadata else None
            if not now:
                from datetime import datetime, timezone

                now = datetime.now(timezone.utc).isoformat()

            item["pk"] = f"USER#{user_id}"
            item["sk"] = f"COMBINED#{now}#{combined_result.request_id}"
            item["entity_type"] = "COMBINED_RESULT"
            item["user_id"] = user_id
            item["request_id"] = combined_result.request_id
            item["createdAt"] = now
            item["updatedAt"] = now

            logger.info(f"Salvando resultado combinado {combined_result.request_id} na tabela de resultados")
            return await self.results_client.put_item(item)

        except Exception as e:
            logger.exception(f"Erro ao salvar resultado combinado na tabela de resultados: {e}")
            raise

    async def get_combined_result(self, image_id: str) -> Optional[CombinedResult]:
        try:
            items = await self.results_client.scan(
                filter_expression="entity_type = :entity_type AND contains(#item, :image_id)",
                expression_values={":entity_type": "COMBINED_RESULT", ":image_id": image_id},
                expression_names={"#item": "image_id"},
            )

            if not items:
                logger.warning(f"Resultado combinado não encontrado para image_id: {image_id}")
                return None

            latest_item = max(items, key=lambda x: x.get("createdAt", ""))
            return CombinedResult.from_dict(latest_item)

        except Exception as e:
            logger.exception(f"Erro ao recuperar resultado combinado da tabela de resultados: {e}")
            raise

    async def save_request_summary(self, item: Dict[str, Any]) -> Dict[str, Any]:
        try:
            logger.info(f"Salvando resumo da requisição {item.get('request_id')} na tabela de resultados")
            return await self.results_client.put_item(item)
        except Exception as e:
            logger.exception(f"Erro ao salvar resumo da requisição na tabela de resultados: {e}")
            raise

    async def get_item(self, key: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            return await self.results_client.get_item(key)
        except Exception as e:
            logger.exception(f"Erro ao recuperar item por chave da tabela de resultados: {e}")
            raise

    async def query_items(
        self,
        key_name: str,
        key_value: Any,
        index_name: Optional[str] = None,
        limit: Optional[int] = None,
        last_evaluated_key: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        try:
            query_kwargs = {
                "KeyConditionExpression": f"{key_name} = :value",
                "ExpressionAttributeValues": {":value": key_value},
            }

            if index_name:
                query_kwargs["IndexName"] = index_name

            if limit:
                query_kwargs["Limit"] = limit

            if last_evaluated_key:
                query_kwargs["ExclusiveStartKey"] = last_evaluated_key

            response = self.results_client.table.query(**query_kwargs)
            items = response.get("Items", [])

            converted_items = [self.results_client.convert_from_dynamo_item(item) for item in items]

            if "LastEvaluatedKey" in response:
                return {"items": converted_items, "last_evaluated_key": response["LastEvaluatedKey"]}

            return {"items": converted_items, "last_evaluated_key": None}

        except Exception as e:
            logger.error(f"Erro ao consultar itens na tabela de resultados: {e}")
            raise

    async def query_results_with_filters(
        self,
        user_id: Optional[str] = None,
        status: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 50,
        last_evaluated_key: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        try:
            if user_id:
                query_kwargs = {
                    "IndexName": "UserIdIndex",
                    "KeyConditionExpression": "user_id = :user_id",
                    "ExpressionAttributeValues": {":user_id": user_id},
                    "ScanIndexForward": False,
                    "Limit": limit * 2,
                }
            else:
                query_kwargs = {
                    "IndexName": "EntityTypeIndex",
                    "KeyConditionExpression": "entity_type = :entity_type",
                    "ExpressionAttributeValues": {":entity_type": "COMBINED_RESULT"},
                    "ScanIndexForward": False,
                    "Limit": limit * 2,
                }

            filter_expressions = []

            if status:
                filter_expressions.append("#status = :status")
                if "ExpressionAttributeNames" not in query_kwargs:
                    query_kwargs["ExpressionAttributeNames"] = {}
                query_kwargs["ExpressionAttributeNames"]["#status"] = "status"
                query_kwargs["ExpressionAttributeValues"][":status"] = status

            if start_date:
                filter_expressions.append("createdAt >= :start_date")
                query_kwargs["ExpressionAttributeValues"][":start_date"] = start_date.isoformat()

            if end_date:
                filter_expressions.append("createdAt <= :end_date")
                query_kwargs["ExpressionAttributeValues"][":end_date"] = end_date.isoformat()

            if filter_expressions:
                query_kwargs["FilterExpression"] = " AND ".join(filter_expressions)

            if last_evaluated_key:
                query_kwargs["ExclusiveStartKey"] = last_evaluated_key

            response = self.results_client.table.query(**query_kwargs)
            items = response.get("Items", [])

            converted_items = []
            for item in items:
                converted_item = self.results_client.convert_from_dynamo_item(item)
                if converted_item.get("entity_type") == "COMBINED_RESULT":
                    converted_items.append(converted_item)
                    if len(converted_items) >= limit:
                        break

            return {
                "items": converted_items[:limit],
                "last_evaluated_key": response.get("LastEvaluatedKey") if len(converted_items) >= limit else None,
            }

        except Exception as e:
            logger.exception(f"Erro ao buscar resultados com filtros: {e}")
            raise

    async def scan(
        self,
        filter_expression: Optional[str] = None,
        expression_values: Optional[Dict[str, Any]] = None,
        expression_names: Optional[Dict[str, str]] = None,
        limit: Optional[int] = None,
        last_evaluated_key: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        try:
            scan_kwargs = {}

            if filter_expression:
                scan_kwargs["FilterExpression"] = filter_expression
            if expression_values:
                scan_kwargs["ExpressionAttributeValues"] = expression_values
            if expression_names:
                scan_kwargs["ExpressionAttributeNames"] = expression_names
            if limit:
                scan_kwargs["Limit"] = limit
            if last_evaluated_key:
                scan_kwargs["ExclusiveStartKey"] = last_evaluated_key

            response = self.results_client.table.scan(**scan_kwargs)
            items = response.get("Items", [])

            return [self.results_client.convert_from_dynamo_item(item) for item in items]

        except Exception as e:
            logger.error(f"Erro ao realizar scan na tabela de resultados: {e}")
            raise
