import json
import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

import boto3

from src.app.config import settings

logger = logging.getLogger(__name__)


def floats_to_decimals(obj: Any) -> Any:
    """Converte floats para Decimal para compatibilidade com DynamoDB."""
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
        """Converte item do DynamoDB para formato padrão."""
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
        """Insere ou atualiza um item no DynamoDB."""
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
        """Recupera um item específico do DynamoDB."""
        try:
            response = self.table.get_item(Key=key)

            if "Item" not in response:
                return None

            return self.convert_from_dynamo_item(response["Item"])
        except Exception as e:
            logger.exception(f"Erro ao recuperar item do DynamoDB: {e}")
            return None

    async def delete_item(self, key: Dict[str, Any]) -> bool:
        """Remove um item do DynamoDB."""
        try:
            self.table.delete_item(Key=key)
            logger.info(f"Item removido com sucesso: {key}")
            return True
        except Exception as e:
            logger.error(f"Erro ao remover item do DynamoDB: {e}")
            return False

    async def query_items(
        self,
        key_name: str,
        key_value: Any,
        index_name: Optional[str] = None,
        limit: Optional[int] = None,
        scan_index_forward: bool = True,
        last_evaluated_key: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Realiza query no DynamoDB com suporte a paginação."""
        try:
            query_kwargs = {
                "KeyConditionExpression": f"{key_name} = :value",
                "ExpressionAttributeValues": {":value": key_value},
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

    async def scan(
        self,
        filter_expression: Optional[str] = None,
        expression_values: Optional[Dict[str, Any]] = None,
        expression_names: Optional[Dict[str, str]] = None,
        limit: Optional[int] = None,
        last_evaluated_key: Optional[Dict[str, Any]] = None,
        index_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Realiza scan no DynamoDB com filtros opcionais.

        Args:
            filter_expression: Expressão de filtro
            expression_values: Valores para a expressão
            expression_names: Nomes de atributos para a expressão
            limit: Número máximo de itens a retornar
            last_evaluated_key: Chave para continuar paginação
            index_name: Nome do índice para usar no scan

        Returns:
            Lista de itens que atendem aos critérios
        """
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

    async def batch_write(
        self, items: List[Dict[str, Any]], delete_keys: Optional[List[Dict[str, Any]]] = None
    ) -> bool:
        """
        Realiza operações de escrita em lote no DynamoDB.

        Args:
            items: Lista de itens para inserir/atualizar
            delete_keys: Lista de chaves para deletar

        Returns:
            True se todas as operações foram bem-sucedidas
        """
        try:
            with self.table.batch_writer() as batch:
                # Inserir/atualizar itens
                for item in items:
                    dynamo_item = floats_to_decimals(item)
                    batch.put_item(Item=dynamo_item)

                # Deletar itens
                if delete_keys:
                    for key in delete_keys:
                        batch.delete_item(Key=key)

            logger.info(
                f"Batch write concluído: {len(items)} inserções/atualizações, {len(delete_keys or [])} deleções"
            )
            return True

        except Exception as e:
            logger.error(f"Erro ao realizar batch write no DynamoDB: {e}")
            return False

    async def update_item(
        self,
        key: Dict[str, Any],
        update_expression: str,
        expression_values: Dict[str, Any],
        expression_names: Optional[Dict[str, str]] = None,
        condition_expression: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Atualiza um item específico no DynamoDB.

        Args:
            key: Chave do item a ser atualizado
            update_expression: Expressão de atualização
            expression_values: Valores para a expressão
            expression_names: Nomes de atributos para a expressão
            condition_expression: Condição para a atualização

        Returns:
            Item atualizado
        """
        try:
            update_kwargs = {
                "Key": key,
                "UpdateExpression": update_expression,
                "ExpressionAttributeValues": floats_to_decimals(expression_values),
                "ReturnValues": "ALL_NEW",
            }

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

    async def query_with_pagination(
        self,
        key_name: str,
        key_value: Any,
        index_name: Optional[str] = None,
        limit: int = 50,
        last_evaluated_key: Optional[Dict[str, Any]] = None,
        scan_index_forward: bool = True,
        filter_expression: Optional[str] = None,
        expression_values: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Realiza query com suporte completo à paginação.

        Returns:
            Dict contendo items e last_evaluated_key
        """
        try:
            query_kwargs = {
                "KeyConditionExpression": f"{key_name} = :value",
                "ExpressionAttributeValues": {":value": key_value},
                "ScanIndexForward": scan_index_forward,
                "Limit": limit,
            }

            if index_name:
                query_kwargs["IndexName"] = index_name

            if last_evaluated_key:
                query_kwargs["ExclusiveStartKey"] = last_evaluated_key

            if filter_expression:
                query_kwargs["FilterExpression"] = filter_expression

            if expression_values:
                query_kwargs["ExpressionAttributeValues"].update(expression_values)

            response = self.table.query(**query_kwargs)
            items = response.get("Items", [])

            converted_items = [self.convert_from_dynamo_item(item) for item in items]

            return {
                "items": converted_items,
                "last_evaluated_key": response.get("LastEvaluatedKey"),
                "count": len(converted_items),
                "scanned_count": response.get("ScannedCount", 0),
            }

        except Exception as e:
            logger.error(f"Erro ao consultar com paginação no DynamoDB: {e}")
            raise

    def get_table_info(self) -> Dict[str, Any]:
        """Obtém informações sobre a tabela."""
        try:
            response = self.table.meta.client.describe_table(TableName=self.table_name)
            table_info = response.get("Table", {})

            return {
                "table_name": table_info.get("TableName"),
                "table_status": table_info.get("TableStatus"),
                "item_count": table_info.get("ItemCount", 0),
                "table_size_bytes": table_info.get("TableSizeBytes", 0),
                "creation_date": table_info.get("CreationDateTime"),
                "global_secondary_indexes": [
                    {
                        "index_name": gsi.get("IndexName"),
                        "key_schema": gsi.get("KeySchema"),
                        "projection": gsi.get("Projection"),
                    }
                    for gsi in table_info.get("GlobalSecondaryIndexes", [])
                ],
            }

        except Exception as e:
            logger.error(f"Erro ao obter informações da tabela: {e}")
            return {}
