import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fruit_detection_shared.infra.external import DynamoClient

from src.app.config import settings

logger = logging.getLogger(__name__)


class DynamoRepository:
    def __init__(self, dynamo_client: Optional[DynamoClient] = None):
        self.dynamo_client = dynamo_client or DynamoClient(table_name=settings.DYNAMODB_TABLE_NAME)
        self.fetch_buffer_size = settings.DYNAMODB_FETCH_BUFFER_SIZE
        self.max_scan_limit = settings.DYNAMODB_MAX_SCAN_LIMIT

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

    async def count_all_results(
        self,
        status_filter: Optional[str] = None,
        user_id: Optional[str] = None,
        device_id: Optional[str] = None,
        exclude_errors: bool = False,
    ) -> Dict[str, Any]:
        try:
            logger.info(
                f"Contando resultados: user={user_id}, device={device_id}, "
                f"status={status_filter}, exclude_err={exclude_errors}"
            )

            filter_expressions = ["entity_type = :entity_type"]
            expression_values = {":entity_type": "COMBINED_RESULT"}
            expression_names = {}

            if status_filter:
                filter_expressions.append("#status = :status")
                expression_values[":status"] = status_filter
                expression_names["#status"] = "status"

            if exclude_errors:
                filter_expressions.append("#status <> :error_status AND #status <> :failed_status")
                expression_values[":error_status"] = "error"
                expression_values[":failed_status"] = "failed"
                expression_names["#status"] = "status"

            if device_id:
                filter_expressions.append(
                    "(initial_metadata.device_id = :device_id OR additional_metadata.device_id = :device_id)"
                )
                expression_values[":device_id"] = device_id

            if user_id:
                count_via_index = await self._count_via_user_index(user_id, status_filter, device_id, exclude_errors)
                return {"total_count": count_via_index}

            items = await self.dynamo_client.scan(
                filter_expression=" AND ".join(filter_expressions),
                expression_values=expression_values,
                expression_names=expression_names if expression_names else None,
                limit=self.max_scan_limit,
            )

            total_count = len(items)
            logger.info(f"Total de resultados contados: {total_count}")

            return {"total_count": total_count}

        except Exception as e:
            logger.exception(f"Erro ao contar resultados: {e}")
            raise

    async def _count_via_user_index(
        self,
        user_id: str,
        status_filter: Optional[str] = None,
        device_id: Optional[str] = None,
        exclude_errors: bool = False,
    ) -> int:
        try:
            items = await self.dynamo_client.query_items(
                key_name="user_id",
                key_value=user_id,
                index_name="UserIdIndex",
                limit=self.max_scan_limit,
                scan_index_forward=False,
            )

            count = 0
            for item in items:
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

                count += 1

            return count

        except Exception as e:
            logger.exception(f"Erro ao contar via user index: {e}")
            raise

    async def get_all_results_with_offset(
        self,
        offset: int = 0,
        limit: int = 20,
        status_filter: Optional[str] = None,
        user_id: Optional[str] = None,
        device_id: Optional[str] = None,
        exclude_errors: bool = False,
    ) -> Dict[str, Any]:
        try:
            logger.info(
                f"Buscando resultados: offset={offset}, limit={limit}, user={user_id}, "
                f"device={device_id}, status={status_filter}, exclude_err={exclude_errors}"
            )

            if user_id:
                return await self._get_results_via_user_index(
                    user_id, offset, limit, status_filter, device_id, exclude_errors
                )

            if status_filter and not device_id and not exclude_errors:
                return await self._get_results_via_status_index(status_filter, offset, limit)

            return await self._get_results_via_entity_type_index(
                offset, limit, status_filter, device_id, exclude_errors
            )

        except Exception as e:
            logger.exception(f"Erro ao buscar resultados com offset: {e}")
            raise

    async def _get_results_via_entity_type_index(
        self,
        offset: int,
        limit: int,
        status_filter: Optional[str] = None,
        device_id: Optional[str] = None,
        exclude_errors: bool = False,
    ) -> Dict[str, Any]:
        try:
            fetch_limit = offset + limit + self.fetch_buffer_size

            all_items = []
            last_key = None
            total_fetched = 0

            while total_fetched < fetch_limit:
                batch_limit = min(1000, fetch_limit - total_fetched)

                query_result = await self.dynamo_client.query_with_pagination(
                    key_name="entity_type",
                    key_value="COMBINED_RESULT",
                    index_name="EntityTypeIndex",
                    limit=batch_limit,
                    last_evaluated_key=last_key,
                    scan_index_forward=False,
                )

                items = query_result.get("items", [])
                if not items:
                    break

                all_items.extend(items)
                total_fetched += len(items)

                last_key = query_result.get("last_evaluated_key")
                if not last_key:
                    break

            filtered_items = []
            for item in all_items:
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

                filtered_items.append(item)

            paginated_items = filtered_items[offset : offset + limit]
            formatted_items = [self._format_result_item(item) for item in paginated_items]

            logger.info(f"Retornando {len(formatted_items)} resultados (offset={offset})")

            return {"items": formatted_items}

        except Exception as e:
            logger.exception(f"Erro ao buscar resultados via entity type index: {e}")
            raise

    async def _get_results_via_status_index(
        self,
        status_filter: str,
        offset: int,
        limit: int,
    ) -> Dict[str, Any]:
        try:
            fetch_limit = offset + limit + self.fetch_buffer_size

            all_items = []
            last_key = None
            total_fetched = 0

            while total_fetched < fetch_limit:
                batch_limit = min(1000, fetch_limit - total_fetched)

                query_result = await self.dynamo_client.query_with_pagination(
                    key_name="status",
                    key_value=status_filter,
                    index_name="StatusCreatedIndex",
                    limit=batch_limit,
                    last_evaluated_key=last_key,
                    scan_index_forward=False,
                )

                items = query_result.get("items", [])
                if not items:
                    break

                combined_results = [item for item in items if item.get("entity_type") == "COMBINED_RESULT"]
                all_items.extend(combined_results)
                total_fetched += len(combined_results)

                last_key = query_result.get("last_evaluated_key")
                if not last_key:
                    break

            paginated_items = all_items[offset : offset + limit]
            formatted_items = [self._format_result_item(item) for item in paginated_items]

            logger.info(f"Retornando {len(formatted_items)} resultados via status index (offset={offset})")

            return {"items": formatted_items}

        except Exception as e:
            logger.exception(f"Erro ao buscar resultados via status index: {e}")
            raise

    async def _get_results_via_user_index(
        self,
        user_id: str,
        offset: int,
        limit: int,
        status_filter: Optional[str] = None,
        device_id: Optional[str] = None,
        exclude_errors: bool = False,
    ) -> Dict[str, Any]:
        try:
            fetch_limit = offset + limit + self.fetch_buffer_size

            all_items = []
            last_key = None
            total_fetched = 0

            while total_fetched < fetch_limit:
                batch_limit = min(1000, fetch_limit - total_fetched)

                query_result = await self.dynamo_client.query_with_pagination(
                    key_name="user_id",
                    key_value=user_id,
                    index_name="UserIdIndex",
                    limit=batch_limit,
                    last_evaluated_key=last_key,
                    scan_index_forward=False,
                )

                items = query_result.get("items", [])
                if not items:
                    break

                all_items.extend(items)
                total_fetched += len(items)

                last_key = query_result.get("last_evaluated_key")
                if not last_key:
                    break

            filtered_items = []
            for item in all_items:
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

                filtered_items.append(item)

            paginated_items = filtered_items[offset : offset + limit]
            formatted_items = [self._format_result_item(item) for item in paginated_items]

            logger.info(f"Retornando {len(formatted_items)} resultados via user index (offset={offset})")

            return {"items": formatted_items}

        except Exception as e:
            logger.exception(f"Erro ao buscar resultados via user index com offset: {e}")
            raise

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
