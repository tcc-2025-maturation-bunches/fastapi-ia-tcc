import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fruit_detection_shared.infra.external import DynamoClient

from src.app.config import settings

logger = logging.getLogger(__name__)


class DynamoRepository:
    def __init__(self, dynamo_client: Optional[DynamoClient] = None):
        self.dynamo_client = dynamo_client or DynamoClient(table_name=settings.DYNAMODB_TABLE_NAME)

    async def get_result_by_request_id(self, request_id: str) -> Optional[Dict[str, Any]]:
        try:
            items = await self.dynamo_client.query_items(
                key_name="request_id", key_value=request_id, index_name="RequestIdIndex"
            )

            combined_results = [item for item in items if item.get("entity_type") == "COMBINED_RESULT"]

            if not combined_results:
                logger.warning(f"Nenhum resultado encontrado para request_id: {request_id}")
                return None

            result = combined_results[0]
            logger.info(f"Resultado encontrado para request_id: {request_id}")
            return self._format_result_item(result)

        except Exception as e:
            logger.exception(f"Erro ao buscar resultado por request_id: {e}")
            raise

    async def get_results_by_image_id(self, image_id: str) -> List[Dict[str, Any]]:
        try:
            items = await self.dynamo_client.query_items(
                key_name="image_id",
                key_value=image_id,
                index_name="ImageIdIndex",
                scan_index_forward=False,
            )

            combined_results = [item for item in items if item.get("entity_type") == "COMBINED_RESULT"]
            results = [self._format_result_item(item) for item in combined_results]

            logger.info(f"Encontrados {len(results)} resultados para image_id: {image_id}")
            return results

        except Exception as e:
            logger.warning(f"ImageIdIndex pode não existir, tentando scan. Erro: {e}")
            try:
                items = await self.dynamo_client.scan(
                    filter_expression="entity_type = :entity_type AND image_id = :image_id",
                    expression_values={":entity_type": "COMBINED_RESULT", ":image_id": image_id},
                )
                results = [self._format_result_item(item) for item in items]
                logger.info(f"Encontrados {len(results)} resultados para image_id via scan: {image_id}")
                return results
            except Exception as scan_error:
                logger.exception(f"Erro ao buscar resultados por image_id via scan: {scan_error}")
                raise

    async def get_results_by_user_id(self, user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        try:
            items = await self.dynamo_client.query_items(
                key_name="user_id", key_value=user_id, index_name="UserIdIndex", limit=limit, scan_index_forward=False
            )

            combined_results = [item for item in items if item.get("entity_type") == "COMBINED_RESULT"]
            results = [self._format_result_item(item) for item in combined_results]

            logger.info(f"Encontrados {len(results)} resultados para user_id: {user_id}")
            return results

        except Exception as e:
            logger.exception(f"Erro ao buscar resultados por user_id: {e}")
            raise

    async def get_results_by_device_id(self, device_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        try:
            filter_expr = (
                "entity_type = :entity_type AND "
                "(initial_metadata.device_id = :device_id OR additional_metadata.device_id = :device_id)"
            )
            items = await self.dynamo_client.scan(
                filter_expression=filter_expr,
                expression_values={":entity_type": "COMBINED_RESULT", ":device_id": device_id},
                limit=limit,
            )

            results = [self._format_result_item(item) for item in items]
            logger.info(f"Encontrados {len(results)} resultados para device_id: {device_id}")
            return results

        except Exception as e:
            logger.exception(f"Erro ao buscar resultados por device_id: {e}")
            raise

    async def get_all_results(
        self,
        limit: int = 20,
        last_evaluated_key: Optional[Dict[str, Any]] = None,
        status_filter: Optional[str] = None,
        user_id: Optional[str] = None,
        device_id: Optional[str] = None,
        exclude_errors: bool = False,
    ) -> Dict[str, Any]:
        logger.info(
            f"Buscando resultados: limit={limit}, user={user_id}, "
            f"device={device_id}, status={status_filter}, exclude_err={exclude_errors}"
        )
        accumulated_items: List[Dict[str, Any]] = []
        current_last_key = last_evaluated_key
        dynamo_query_count = 0
        max_dynamo_queries = 10

        while len(accumulated_items) < limit and dynamo_query_count < max_dynamo_queries:
            dynamo_query_count += 1
            logger.debug(f"Consulta DynamoDB #{dynamo_query_count}, last_key={current_last_key}")

            dynamo_limit = max(limit * 2, 50)

            try:
                if user_id:
                    query_result = await self.dynamo_client.query_with_pagination(
                        key_name="user_id",
                        key_value=user_id,
                        index_name="UserIdIndex",
                        limit=dynamo_limit,
                        last_evaluated_key=current_last_key,
                        scan_index_forward=False,
                    )
                elif status_filter and not device_id and not exclude_errors:
                    query_result = await self.dynamo_client.query_with_pagination(
                        key_name="status",
                        key_value=status_filter,
                        index_name="StatusCreatedIndex",
                        limit=dynamo_limit,
                        last_evaluated_key=current_last_key,
                        scan_index_forward=False,
                    )
                else:
                    query_result = await self.dynamo_client.query_with_pagination(
                        key_name="entity_type",
                        key_value="COMBINED_RESULT",
                        index_name="EntityTypeIndex",
                        limit=dynamo_limit,
                        last_evaluated_key=current_last_key,
                        scan_index_forward=False,
                    )

                items_from_db = query_result.get("items", [])
                dynamo_last_key = query_result.get("last_evaluated_key")

                for item in items_from_db:
                    if item.get("entity_type") != "COMBINED_RESULT":
                        continue

                    item_status = item.get("status", "")

                    if exclude_errors and item_status in ["error", "failed"]:
                        continue

                    if status_filter and item_status != status_filter:
                        continue

                    if device_id:
                        initial_metadata = item.get("initial_metadata", {})
                        additional_metadata = item.get("additional_metadata", {})
                        item_device_id = initial_metadata.get("device_id") or additional_metadata.get("device_id")

                        if item_device_id != device_id:
                            continue

                    accumulated_items.append(self._format_result_item(item))

                    if len(accumulated_items) >= limit:
                        break

                current_last_key = dynamo_last_key

                if not current_last_key or len(accumulated_items) >= limit:
                    break

            except Exception as e:
                logger.exception(f"Erro durante a consulta paginada ao DynamoDB: {e}")
                raise

        next_api_key = current_last_key if len(accumulated_items) >= limit and current_last_key else None

        logger.info(f"Retornando {len(accumulated_items)} resultados. Próxima chave API: {next_api_key is not None}")

        return {"items": accumulated_items, "last_evaluated_key": next_api_key}

    async def get_results_with_filters(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        status_filter: Optional[str] = None,
        device_id: Optional[str] = None,
        limit: int = 1000,
    ) -> Dict[str, Any]:
        try:
            filter_expressions = ["entity_type = :entity_type"]
            expression_values = {":entity_type": "COMBINED_RESULT"}

            if status_filter:
                filter_expressions.append("#status = :status")
                expression_values[":status"] = status_filter

            if start_date:
                filter_expressions.append("created_at >= :start_date")
                expression_values[":start_date"] = start_date.isoformat()

            if end_date:
                filter_expressions.append("created_at <= :end_date")
                expression_values[":end_date"] = end_date.isoformat()

            if device_id:
                filter_expressions.append(
                    "(initial_metadata.device_id = :device_id OR additional_metadata.device_id = :device_id)"
                )
                expression_values[":device_id"] = device_id

            expression_names = {}
            if status_filter:
                expression_names["#status"] = "status"

            items = await self.dynamo_client.scan(
                filter_expression=" AND ".join(filter_expressions),
                expression_values=expression_values,
                expression_names=expression_names if expression_names else None,
                limit=limit,
            )

            formatted_items = [self._format_result_item(item) for item in items]

            return {"items": formatted_items}

        except Exception as e:
            logger.exception(f"Erro ao buscar resultados com filtros: {e}")
            raise

    def _format_result_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        initial_metadata = item.get("initial_metadata", {})
        additional_metadata = item.get("additional_metadata", {})

        device_id = initial_metadata.get("device_id") or additional_metadata.get("device_id")

        return {
            "request_id": item.get("request_id"),
            "image_id": item.get("image_id"),
            "user_id": item.get("user_id"),
            "device_id": device_id,
            "status": item.get("status"),
            "created_at": item.get("created_at"),
            "updated_at": item.get("updated_at"),
            "processing_time_ms": item.get("processing_time_ms"),
            "image_url": item.get("image_url"),
            "image_result_url": item.get("image_result_url"),
            "detection_result": item.get("detection_result"),
            "processing_metadata": item.get("processing_metadata"),
            "initial_metadata": item.get("initial_metadata"),
            "additional_metadata": item.get("additional_metadata"),
            "error_info": item.get("error_info"),
        }
