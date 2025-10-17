import logging
from typing import Any, Dict, List, Optional

from fruit_detection_shared.infra.external import DynamoClient

from src.app.config import settings

logger = logging.getLogger(__name__)


class DynamoRepository:
    def __init__(self, dynamo_client: Optional[DynamoClient] = None):
        self.dynamo_client = dynamo_client or DynamoClient(table_name=settings.DYNAMODB_TABLE_NAME)

    async def put_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        try:
            logger.debug(f"Inserindo item: pk={item.get('pk')}")
            return await self.dynamo_client.put_item(item)
        except Exception as e:
            logger.exception(f"Erro ao inserir item no DynamoDB: {e}")
            raise

    async def get_item(self, key: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            return await self.dynamo_client.get_item(key)
        except Exception as e:
            logger.exception(f"Erro ao recuperar item do DynamoDB: {e}")
            return None

    async def update_item(
        self,
        key: Dict[str, Any],
        update_expression: str,
        expression_values: Optional[Dict[str, Any]] = None,
        expression_names: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        try:
            return await self.dynamo_client.update_item(
                key=key,
                update_expression=update_expression,
                expression_values=expression_values,
                expression_names=expression_names,
            )
        except Exception as e:
            logger.exception(f"Erro ao atualizar item no DynamoDB: {e}")
            raise

    async def query_items(
        self,
        key_name: str,
        key_value: Any,
        index_name: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        try:
            return await self.dynamo_client.query_items(
                key_name=key_name,
                key_value=key_value,
                index_name=index_name,
                limit=limit,
            )
        except Exception as e:
            logger.exception(f"Erro ao consultar itens no DynamoDB: {e}")
            raise

    async def get_processing_status(self, request_id: str) -> Optional[Dict[str, Any]]:
        key = {"pk": f"STATUS#{request_id}", "sk": "INFO"}
        return await self.get_item(key)

    async def update_processing_status(
        self,
        request_id: str,
        status_data: Dict[str, Any],
    ) -> None:
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

        try:
            await self.update_item(
                key=key,
                update_expression=update_expression,
                expression_values=expression_values,
                expression_names=expression_names if expression_names else None,
            )
            logger.debug(f"Status atualizado para request_id: {request_id}")
        except Exception as e:
            logger.warning(f"Erro ao atualizar status: {e}")
            raise
