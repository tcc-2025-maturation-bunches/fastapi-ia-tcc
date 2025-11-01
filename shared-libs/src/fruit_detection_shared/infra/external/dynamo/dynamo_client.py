import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

import aioboto3
from botocore.exceptions import ClientError

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
    _session: Optional[aioboto3.Session] = None

    def __init__(self, table_name: str, region: str = "us-east-1"):
        if not table_name:
            raise ValueError("table_name é obrigatório")

        self.table_name = table_name
        self.region = region

        if DynamoClient._session is None:
            DynamoClient._session = aioboto3.Session()

        self.session = DynamoClient._session
        logger.info(f"Inicializando cliente DynamoDB assíncrono para tabela {self.table_name}")

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
            else:
                result[key] = value
        return result

    async def put_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        dynamo_item = floats_to_decimals(item)

        async with self.session.resource("dynamodb", region_name=self.region) as dynamodb:
            table = await dynamodb.Table(self.table_name)

            try:
                await table.put_item(Item=dynamo_item)
                pk_value = dynamo_item.get("PK") or dynamo_item.get("pk")
                logger.debug(f"Item inserido: pk={pk_value}")
                return dynamo_item
            except Exception as e:
                logger.error(f"Erro ao inserir item no DynamoDB: {e}")
                raise

    async def get_item(self, key: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        async with self.session.resource("dynamodb", region_name=self.region) as dynamodb:
            table = await dynamodb.Table(self.table_name)

            try:
                response = await table.get_item(Key=key)
                if "Item" not in response:
                    return None
                return self.convert_from_dynamo_item(response["Item"])
            except Exception as e:
                logger.exception(f"Erro ao recuperar item: {e}")
                return None

    async def delete_item(self, key: Dict[str, Any]) -> bool:
        async with self.session.resource("dynamodb", region_name=self.region) as dynamodb:
            table = await dynamodb.Table(self.table_name)

            try:
                await table.delete_item(Key=key)
                logger.debug(f"Item removido: {key}")
                return True
            except Exception as e:
                logger.error(f"Erro ao remover item: {e}")
                return False

    async def update_item(
        self,
        key: Dict[str, Any],
        update_expression: str,
        expression_values: Optional[Dict[str, Any]] = None,
        expression_names: Optional[Dict[str, str]] = None,
        condition_expression: Optional[str] = None,
    ) -> Dict[str, Any]:
        async with self.session.resource("dynamodb", region_name=self.region) as dynamodb:
            table = await dynamodb.Table(self.table_name)

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

                response = await table.update_item(**update_kwargs)
                updated_item = response.get("Attributes", {})
                logger.debug(f"Item atualizado: {key}")
                return self.convert_from_dynamo_item(updated_item)
            except Exception as e:
                logger.error(f"Erro ao atualizar item: {e}")
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
        async with self.session.resource("dynamodb", region_name=self.region) as dynamodb:
            table = await dynamodb.Table(self.table_name)

            try:
                from boto3.dynamodb.conditions import Key

                query_kwargs = {
                    "KeyConditionExpression": Key(key_name).eq(key_value),
                    "ScanIndexForward": scan_index_forward,
                }

                if index_name:
                    query_kwargs["IndexName"] = index_name
                if limit:
                    query_kwargs["Limit"] = limit
                if last_evaluated_key:
                    query_kwargs["ExclusiveStartKey"] = last_evaluated_key

                response = await table.query(**query_kwargs)
                items = response.get("Items", [])
                return [self.convert_from_dynamo_item(item) for item in items]
            except Exception as e:
                logger.error(f"Erro ao consultar itens: {e}")
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
        async with self.session.resource("dynamodb", region_name=self.region) as dynamodb:
            table = await dynamodb.Table(self.table_name)

            try:
                from boto3.dynamodb.conditions import Attr, Key

                query_kwargs = {
                    "KeyConditionExpression": Key(key_name).eq(key_value),
                    "ScanIndexForward": scan_index_forward,
                }

                if index_name:
                    query_kwargs["IndexName"] = index_name
                if limit:
                    query_kwargs["Limit"] = limit
                if last_evaluated_key:
                    query_kwargs["ExclusiveStartKey"] = last_evaluated_key

                if filter_expression:
                    conditions = []
                    for part in filter_expression.split(" AND "):
                        part = part.strip()

                        if " >= " in part:
                            attr, value_key = part.split(" >= ")
                            attr = attr.strip().replace("#", "")
                            value_key = value_key.strip()
                            if expression_names and f"#{attr}" in expression_names:
                                attr = expression_names[f"#{attr}"]
                            if expression_values and value_key in expression_values:
                                conditions.append(Attr(attr).gte(expression_values[value_key]))

                        elif " <= " in part:
                            attr, value_key = part.split(" <= ")
                            attr = attr.strip().replace("#", "")
                            value_key = value_key.strip()
                            if expression_names and f"#{attr}" in expression_names:
                                attr = expression_names[f"#{attr}"]
                            if expression_values and value_key in expression_values:
                                conditions.append(Attr(attr).lte(expression_values[value_key]))

                        elif " <> " in part:
                            attr, value_key = part.split(" <> ")
                            attr = attr.strip().replace("#", "")
                            value_key = value_key.strip()
                            if expression_names and f"#{attr}" in expression_names:
                                attr = expression_names[f"#{attr}"]
                            if expression_values and value_key in expression_values:
                                conditions.append(Attr(attr).ne(expression_values[value_key]))

                        elif " = " in part:
                            attr, value_key = part.split(" = ")
                            attr = attr.strip().replace("#", "")
                            value_key = value_key.strip()
                            if expression_names and f"#{attr}" in expression_names:
                                attr = expression_names[f"#{attr}"]
                            if expression_values and value_key in expression_values:
                                conditions.append(Attr(attr).eq(expression_values[value_key]))

                    if conditions:
                        combined_filter = conditions[0]
                        for condition in conditions[1:]:
                            combined_filter = combined_filter & condition
                        query_kwargs["FilterExpression"] = combined_filter

                response = await table.query(**query_kwargs)
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
                logger.error(f"Erro ao consultar com paginação: {e}")
                raise

    async def get_table_info(self) -> Dict[str, Any]:
        async with self.session.client("dynamodb", region_name=self.region) as client:
            try:
                response = await client.describe_table(TableName=self.table_name)
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

    async def scan(
        self,
        filter_expression: Optional[str] = None,
        expression_values: Optional[Dict[str, Any]] = None,
        expression_names: Optional[Dict[str, str]] = None,
        limit: Optional[int] = None,
        last_evaluated_key: Optional[Dict[str, Any]] = None,
        index_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        async with self.session.resource("dynamodb", region_name=self.region) as dynamodb:
            table = await dynamodb.Table(self.table_name)

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

                response = await table.scan(**scan_kwargs)
                items = response.get("Items", [])
                converted_items = [self.convert_from_dynamo_item(item) for item in items]
                logger.debug(f"Scan retornou {len(converted_items)} itens")
                return converted_items
            except Exception as e:
                logger.error(f"Erro ao realizar scan: {e}")
                raise

    async def batch_get_items(self, keys: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        async with self.session.resource("dynamodb", region_name=self.region) as dynamodb:
            try:
                response = await dynamodb.batch_get_item(RequestItems={self.table_name: {"Keys": keys}})

                items = response.get("Responses", {}).get(self.table_name, [])
                return [self.convert_from_dynamo_item(item) for item in items]
            except Exception as e:
                logger.error(f"Erro ao recuperar itens em lote: {e}")
                raise

    async def batch_write_items(self, items: List[Dict[str, Any]]) -> bool:
        async with self.session.resource("dynamodb", region_name=self.region) as dynamodb:
            table = await dynamodb.Table(self.table_name)

            try:
                async with table.batch_writer() as batch:
                    for item in items:
                        dynamo_item = floats_to_decimals(item)
                        await batch.put_item(Item=dynamo_item)

                logger.info(f"Batch write de {len(items)} itens concluído")
                return True
            except Exception as e:
                logger.error(f"Erro ao escrever itens em lote: {e}")
                return False
