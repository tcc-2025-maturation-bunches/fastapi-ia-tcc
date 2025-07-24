import json
import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

import boto3
from botocore.exceptions import ClientError

from src.app.config import settings

logger = logging.getLogger(__name__)


def floats_to_decimals(obj: Any) -> Any:
    if isinstance(obj, list):
        return [floats_to_decimals(i) for i in obj]
    if isinstance(obj, dict):
        return {k: floats_to_decimals(v) for k, v in obj.items()}
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

    async def delete_item(self, key: Dict[str, Any]) -> bool:
        try:
            self.table.delete_item(Key=key)
            logger.info(f"Item removido com sucesso: {key}")
            return True
        except Exception as e:
            logger.error(f"Erro ao remover item do DynamoDB: {e}")
            return False

    async def update_item(
        self,
        key: Dict[str, Any],
        update_expression: str,
        expression_values: Optional[Dict[str, Any]] = None,
        expression_names: Optional[Dict[str, str]] = None,
        condition_expression: Optional[str] = None,
    ) -> Dict[str, Any]:
        try:
            update_kwargs = {
                "Key": key,
                "UpdateExpression": update_expression,
                "ReturnValues": "ALL_NEW",
            }

            if expression_values:
                update_kwargs["ExpressionAttributeValues"] = floats_to_decimals(expression_values)
            if expression_names:
                update_kwargs["ExpressionAttributeNames"] = expression_names
            if condition_expression:
                update_kwargs["ConditionExpression"] = condition_expression

            response = self.table.update_item(**update_kwargs)
            updated_item = response.get("Attributes", {})

            logger.info(f"Item atualizado com sucesso: {key}")
            return self.convert_from_dynamo_item(updated_item)
        except Exception as e:
            logger.error(f"Erro ao atualizar item no DynamoDB: {e}")
            raise

    async def query_items(
        self,
        key_name: str,
        key_value: Any,
        index_name: Optional[str] = None,
        limit: Optional[int] = None,
        scan_index_forward: bool = True,
        last_evaluated_key: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        try:
            query_kwargs = {
                "KeyConditionExpression": "#key_name = :value",
                "ExpressionAttributeValues": {":value": key_value},
                "ExpressionAttributeNames": {"#key_name": key_name},
                "ScanIndexForward": scan_index_forward,
            }

            if index_name:
                query_kwargs["IndexName"] = index_name

            if limit:
                query_kwargs["Limit"] = limit

            if last_evaluated_key:
                query_kwargs["ExclusiveStartKey"] = last_evaluated_key

            response = self.table.query(**query_kwargs)
            items = response.get("Items", [])

            return [self.convert_from_dynamo_item(item) for item in items]
        except Exception as e:
            logger.error(f"Erro ao consultar itens no DynamoDB: {e}")
            raise

    async def query_with_pagination(
        self,
        key_name: str,
        key_value: Any,
        index_name: Optional[str] = None,
        limit: Optional[int] = None,
        scan_index_forward: bool = True,
        last_evaluated_key: Optional[Dict[str, Any]] = None,
        filter_expression: Optional[str] = None,
        expression_values: Optional[Dict[str, Any]] = None,
        expression_names: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        try:
            query_kwargs = {
                "KeyConditionExpression": "#key_name = :key_value",
                "ExpressionAttributeNames": {"#key_name": key_name},
                "ExpressionAttributeValues": {":key_value": key_value},
                "ScanIndexForward": scan_index_forward,
            }

            if expression_values:
                query_kwargs["ExpressionAttributeValues"].update(expression_values)

            if index_name:
                query_kwargs["IndexName"] = index_name

            if limit:
                query_kwargs["Limit"] = limit

            if last_evaluated_key:
                query_kwargs["ExclusiveStartKey"] = last_evaluated_key

            if filter_expression:
                query_kwargs["FilterExpression"] = filter_expression

            if expression_names:
                query_kwargs["ExpressionAttributeNames"] = expression_names

            response = self.table.query(**query_kwargs)

            items = [self.convert_from_dynamo_item(item) for item in response.get("Items", [])]

            result = {
                "items": items,
                "count": response.get("Count", 0),
                "scanned_count": response.get("ScannedCount", 0),
            }

            if "LastEvaluatedKey" in response:
                result["last_evaluated_key"] = response["LastEvaluatedKey"]

            return result
        except Exception as e:
            logger.error(f"Erro ao consultar itens com paginação no DynamoDB: {e}")
            raise

    def get_table_info(self) -> Dict[str, Any]:
        try:
            response = self.table.meta.client.describe_table(TableName=self.table_name)
            table_info = response["Table"]

            result = {
                "table_name": table_info["TableName"],
                "table_status": table_info["TableStatus"],
                "item_count": table_info.get("ItemCount", 0),
                "table_size_bytes": table_info.get("TableSizeBytes", 0),
                "creation_date_time": table_info.get("CreationDateTime"),
                "global_secondary_indexes": [],
            }

            if "GlobalSecondaryIndexes" in table_info:
                for gsi in table_info["GlobalSecondaryIndexes"]:
                    gsi_info = {
                        "index_name": gsi["IndexName"],
                        "key_schema": gsi["KeySchema"],
                        "projection": gsi["Projection"],
                    }
                    result["global_secondary_indexes"].append(gsi_info)

            return result
        except ClientError as e:
            logger.error(f"Erro ao obter informações da tabela: {e}")
            return {}
        except Exception as e:
            logger.error(f"Erro inesperado ao obter informações da tabela: {e}")
            return {}

    async def scan(
        self,
        filter_expression: Optional[str] = None,
        expression_values: Optional[Dict[str, Any]] = None,
        expression_names: Optional[Dict[str, str]] = None,
        limit: Optional[int] = None,
        last_evaluated_key: Optional[Dict[str, Any]] = None,
        index_name: Optional[str] = None,
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
            if index_name:
                scan_kwargs["IndexName"] = index_name

            response = self.table.scan(**scan_kwargs)
            items = response.get("Items", [])

            converted_items = [self.convert_from_dynamo_item(item) for item in items]

            logger.info(f"Scan retornou {len(converted_items)} itens")
            return converted_items

        except Exception as e:
            logger.error(f"Erro ao realizar scan no DynamoDB: {e}")
            raise
