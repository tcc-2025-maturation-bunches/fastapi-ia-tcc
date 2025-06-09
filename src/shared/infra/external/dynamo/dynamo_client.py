import json
import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

import boto3

from src.app.config import settings

logger = logging.getLogger(__name__)


def floats_to_decimals(obj: Any, *, _is_root: bool = True) -> Any:
    if isinstance(obj, list):
        if not _is_root:
            return json.dumps([floats_to_decimals(i, _is_root=False) for i in obj])
        return [floats_to_decimals(i, _is_root=False) for i in obj]
    if isinstance(obj, dict):
        if not _is_root:
            return json.dumps({k: floats_to_decimals(v, _is_root=False) for k, v in obj.items()})
        return {k: floats_to_decimals(v, _is_root=False) for k, v in obj.items()}
    if isinstance(obj, float):
        return Decimal(str(obj))
    if isinstance(obj, datetime):
        return obj.isoformat()
    return obj


class DynamoClient:
    def __init__(self, table_name: Optional[str] = None, region: Optional[str] = None):
        self.table_name = table_name or settings.DYNAMODB_TABLE_NAME
        self.region = region or settings.AWS_REGION
        self.client = boto3.resource("dynamodb", region_name=self.region)
        self.table = self.client.Table(self.table_name)
        logger.info(f"Inicializando cliente DynamoDB para tabela {self.table_name}")

    def convert_from_dynamo_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        if not item:
            return {}

        result = {}
        for key, value in item.items():
            if key.endswith("_timestamp") and isinstance(value, str):
                try:
                    result[key] = datetime.fromisoformat(value)
                except ValueError:
                    result[key] = value
            elif key in ["results", "metadata", "summary"] and isinstance(value, str):
                try:
                    result[key] = json.loads(value)
                except json.JSONDecodeError:
                    result[key] = value
            else:
                result[key] = value
        return result

    async def put_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        dynamo_item = floats_to_decimals(item)

        try:
            self.table.put_item(Item=dynamo_item)
            pk_value = dynamo_item.get("PK") or dynamo_item.get("pk")
            logger.info(f"Item inserido com sucesso: pk={pk_value}")
            return dynamo_item
        except Exception as e:
            logger.error(f"Erro ao inserir item no DynamoDB: {e}")
            raise

    async def get_item(self, key: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            response = self.table.get_item(Key=key)

            if "Item" not in response:
                return None

            return self.convert_from_dynamo_item(response["Item"])
        except Exception as e:
            logger.exception(f"Erro ao recuperar item do DynamoDB: {e}")
            return None

    async def query_items(
        self, key_name: str, key_value: Any, index_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        try:
            query_kwargs = {
                "KeyConditionExpression": f"{key_name} = :value",
                "ExpressionAttributeValues": {":value": key_value},
            }

            if index_name:
                query_kwargs["IndexName"] = index_name

            response = self.table.query(**query_kwargs)
            items = response.get("Items", [])

            return [self.convert_from_dynamo_item(item) for item in items]
        except Exception as e:
            logger.error(f"Erro ao consultar itens no DynamoDB: {e}")
            raise
