import logging
from datetime import datetime, timezone
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
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        exclude_errors: bool = False,
    ) -> Dict[str, Any]:
        try:
            logger.info(
                f"Contando resultados: user={user_id}, device={device_id}, "
                f"status={status_filter}, start={start_date}, end={end_date}, exclude_err={exclude_errors}"
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

            if user_id:
                count_via_index = await self._count_via_user_index(
                    user_id, status_filter, device_id, start_date, end_date, exclude_errors
                )
                return {"total_count": count_via_index}

            count = await self._count_via_entity_type_index(
                status_filter=status_filter,
                device_id=device_id,
                start_date=start_date,
                end_date=end_date,
                exclude_errors=exclude_errors,
            )

            logger.info(f"Total de resultados contados via EntityTypeIndex: {count}")
            return {"total_count": count}

        except Exception as e:
            logger.exception(f"Erro ao contar resultados: {e}")
            raise

    async def _count_via_user_index(
        self,
        user_id: str,
        status_filter: Optional[str] = None,
        device_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
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
                if self._matches_all_filters(item, status_filter, device_id, start_date, end_date, exclude_errors):
                    count += 1

            return count
        except Exception as e:
            logger.exception(f"Erro ao contar via user index: {e}")
            raise

    async def _count_via_entity_type_index(
        self,
        status_filter: Optional[str] = None,
        device_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        exclude_errors: bool = False,
    ) -> int:
        try:
            count = 0
            last_key = None

            logger.info("Contando resultados via EntityTypeIndex (query)")

            while True:
                query_result = await self.dynamo_client.query_with_pagination(
                    key_name="entity_type",
                    key_value="COMBINED_RESULT",
                    index_name="EntityTypeIndex",
                    limit=self.max_scan_limit,
                    last_evaluated_key=last_key,
                    scan_index_forward=False,
                )

                items = query_result.get("items", [])
                if not items:
                    break

                for item in items:
                    if self._matches_all_filters(item, status_filter, device_id, start_date, end_date, exclude_errors):
                        count += 1

                last_key = query_result.get("last_evaluated_key")
                if not last_key:
                    break

                if count > 0 and count % 1000 == 0:
                    logger.info(f"Contagem em progresso: {count} itens encontrados até agora")

            logger.info(f"Contagem finalizada via EntityTypeIndex: {count} resultados")
            return count

        except Exception as e:
            logger.exception(f"Erro ao contar via entity type index: {e}")
            raise

    def _matches_status_filter(self, item: Dict[str, Any], status_filter: Optional[str], exclude_errors: bool) -> bool:
        if not status_filter and not exclude_errors:
            return True

        item_status = item.get("status", "")

        if exclude_errors and item_status in ["error", "failed"]:
            return False

        if status_filter and item_status != status_filter:
            return False

        return True

    def _matches_date_range(
        self, item: Dict[str, Any], start_date: Optional[datetime], end_date: Optional[datetime]
    ) -> bool:
        if not start_date and not end_date:
            return True

        created_at_str = item.get("created_at")
        if not created_at_str:
            return False

        try:
            created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))

            if not created_at.tzinfo:
                created_at = created_at.replace(tzinfo=timezone.utc)

            if start_date:
                start_date_aware = start_date if start_date.tzinfo else start_date.replace(tzinfo=timezone.utc)
                if created_at < start_date_aware:
                    return False

            if end_date:
                end_date_aware = end_date if end_date.tzinfo else end_date.replace(tzinfo=timezone.utc)
                if created_at > end_date_aware:
                    return False

            return True
        except ValueError:
            return False

    def _matches_device_id(self, item: Dict[str, Any], device_id: Optional[str]) -> bool:
        if not device_id:
            return True

        initial_metadata = item.get("initial_metadata", {})
        additional_metadata = item.get("additional_metadata", {})
        item_device_id = initial_metadata.get("device_id") or additional_metadata.get("device_id")

        return item_device_id == device_id

    def _calculate_batch_limit(self, needed_items: int, filtered_count: int, items_skipped: int) -> int:
        remaining_items = needed_items - filtered_count - items_skipped
        batch_size = remaining_items + self.fetch_buffer_size
        return min(self.max_scan_limit, max(1, batch_size))

    def _should_use_status_index(
        self,
        status_filter: Optional[str],
        device_id: Optional[str],
        start_date: Optional[datetime],
        end_date: Optional[datetime],
        exclude_errors: bool,
    ) -> bool:
        return (
            status_filter is not None
            and device_id is None
            and start_date is None
            and end_date is None
            and not exclude_errors
        )

    async def get_all_results_with_offset(
        self,
        offset: int = 0,
        limit: int = 20,
        status_filter: Optional[str] = None,
        user_id: Optional[str] = None,
        device_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        exclude_errors: bool = False,
    ) -> Dict[str, Any]:
        try:
            logger.info(
                f"Buscando resultados: offset={offset}, limit={limit}, user={user_id}, "
                f"device={device_id}, status={status_filter}, start={start_date}, end={end_date}, "
                f"exclude_err={exclude_errors}"
            )

            if user_id:
                return await self._get_results_via_user_index(
                    user_id, offset, limit, status_filter, device_id, start_date, end_date, exclude_errors
                )

            if self._should_use_status_index(status_filter, device_id, start_date, end_date, exclude_errors):
                return await self._get_results_via_status_index(status_filter, offset, limit)

            return await self._get_results_via_entity_type_index(
                offset, limit, status_filter, device_id, start_date, end_date, exclude_errors
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
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        exclude_errors: bool = False,
    ) -> Dict[str, Any]:
        try:
            filtered_items = []
            last_key = None
            total_filtered = 0
            needed_items = offset + limit

            while total_filtered < needed_items:
                batch_limit = min(self.max_scan_limit, needed_items - total_filtered + self.fetch_buffer_size)

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

                for item in items:
                    if total_filtered >= needed_items:
                        break

                    if item.get("entity_type") != "COMBINED_RESULT":
                        continue

                    if not self._matches_status_filter(item, status_filter, exclude_errors):
                        continue

                    if not self._matches_date_range(item, start_date, end_date):
                        continue

                    if not self._matches_device_id(item, device_id):
                        continue

                    filtered_items.append(item)
                    total_filtered += 1

                last_key = query_result.get("last_evaluated_key")
                if not last_key:
                    break

            paginated_items = filtered_items[offset : offset + limit]
            formatted_items = [self._format_result_item(item) for item in paginated_items]

            logger.info(
                f"Retornando {len(formatted_items)} resultados (offset={offset}, " f"total_filtered={total_filtered})"
            )

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
                batch_limit = min(self.max_scan_limit, fetch_limit - total_fetched)

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
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        exclude_errors: bool = False,
    ) -> Dict[str, Any]:
        try:
            filtered_items = []
            filtered_count = 0  # Track count separately for performance
            items_skipped = 0
            last_key = None
            needed_items = offset + limit

            while filtered_count < limit:
                batch_limit = self._calculate_batch_limit(needed_items, filtered_count, items_skipped)

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

                for item in items:
                    if filtered_count >= limit:
                        break

                    if not self._matches_all_filters(
                        item, status_filter, device_id, start_date, end_date, exclude_errors
                    ):
                        continue

                    if items_skipped < offset:
                        items_skipped += 1
                        continue

                    filtered_items.append(item)
                    filtered_count += 1

                last_key = query_result.get("last_evaluated_key")

                if not last_key or filtered_count >= limit:
                    break

            formatted_items = [self._format_result_item(item) for item in filtered_items]

            logger.info(
                f"Retornando {len(formatted_items)} resultados via user index (offset={offset}, "
                f"items_skipped={items_skipped})"
            )

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
            if status_filter and start_date and not device_id:
                return await self._get_results_via_status_created_index_with_date_range(
                    status_filter, start_date, end_date
                )

            if start_date and not status_filter and not device_id:
                return await self._get_all_results_via_status_index_with_date_range(start_date, end_date)

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

    async def _get_results_via_status_created_index_with_date_range(
        self,
        status: str,
        start_date: datetime,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        try:
            all_items = []
            last_key = None

            logger.info(
                f"Buscando resultados via StatusCreatedIndex: status={status}, "
                f"start_date={start_date.isoformat()}, end_date={end_date.isoformat() if end_date else 'None'}"
            )

            while True:
                query_result = await self.dynamo_client.query_with_pagination(
                    key_name="status",
                    key_value=status,
                    index_name="StatusCreatedIndex",
                    limit=self.max_scan_limit,
                    last_evaluated_key=last_key,
                    scan_index_forward=False,
                )

                items = query_result.get("items", [])
                if not items:
                    break

                for item in items:
                    if item.get("entity_type") != "COMBINED_RESULT":
                        continue

                    if not self._matches_date_range(item, start_date, end_date):
                        continue

                    all_items.append(item)

                last_key = query_result.get("last_evaluated_key")

                if not last_key:
                    break

                logger.debug(f"Coletados {len(all_items)} itens até agora, continuando paginação...")

            formatted_items = [self._format_result_item(item) for item in all_items]

            logger.info(f"Total de {len(formatted_items)} resultados encontrados via StatusCreatedIndex")

            return {"items": formatted_items}

        except Exception as e:
            logger.exception(f"Erro ao buscar via StatusCreatedIndex com date range: {e}")
            raise

    async def _get_all_results_via_status_index_with_date_range(
        self,
        start_date: datetime,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        try:
            all_statuses = ["completed", "success", "processing", "pending", "error", "failed"]
            all_items = []

            logger.info(
                f"Buscando todos os resultados via StatusCreatedIndex: "
                f"start_date={start_date.isoformat()}, end_date={end_date.isoformat() if end_date else 'None'}"
            )

            for status in all_statuses:
                try:
                    result = await self._get_results_via_status_created_index_with_date_range(
                        status, start_date, end_date
                    )
                    items = result.get("items", [])
                    all_items.extend(items)
                    logger.debug(f"Status '{status}': {len(items)} itens encontrados")
                except Exception as e:
                    logger.warning(f"Erro ao buscar status '{status}': {e}, continuando...")
                    continue

            logger.info(f"Total de {len(all_items)} resultados encontrados em todos os status")

            return {"items": all_items}

        except Exception as e:
            logger.exception(f"Erro ao buscar todos os resultados via status index: {e}")
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

    def _matches_all_filters(
        self,
        item: Dict[str, Any],
        status_filter: Optional[str] = None,
        device_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        exclude_errors: bool = False,
    ) -> bool:
        if item.get("entity_type") != "COMBINED_RESULT":
            return False
        if not self._matches_status_filter(item, status_filter, exclude_errors):
            return False
        if not self._matches_date_range(item, start_date, end_date):
            return False
        if not self._matches_device_id(item, device_id):
            return False
        return True

    async def count_all_results_optimized(
        self,
        status_filter: Optional[str] = None,
        user_id: Optional[str] = None,
        device_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        exclude_errors: bool = False,
    ) -> Dict[str, Any]:
        try:
            logger.info("Usando contagem otimizada com FilterExpression")

            filter_parts = []
            expression_values = {}
            expression_names = {}

            if status_filter:
                filter_parts.append("#status = :status")
                expression_values[":status"] = status_filter
                expression_names["#status"] = "status"

            if exclude_errors:
                filter_parts.append("#status <> :error_status")
                filter_parts.append("#status <> :failed_status")
                expression_values[":error_status"] = "error"
                expression_values[":failed_status"] = "failed"
                expression_names["#status"] = "status"

            if start_date:
                filter_parts.append("created_at >= :start_date")
                expression_values[":start_date"] = start_date.isoformat()

            if end_date:
                filter_parts.append("created_at <= :end_date")
                expression_values[":end_date"] = end_date.isoformat()

            filter_expression = " AND ".join(filter_parts) if filter_parts else None

            if user_id:
                return await self._count_via_user_index_optimized(
                    user_id, filter_expression, expression_values, expression_names, device_id
                )

            return await self._count_via_entity_type_index_optimized(
                filter_expression, expression_values, expression_names, device_id
            )

        except Exception as e:
            logger.exception(f"Erro ao contar resultados otimizado: {e}")
            raise

    async def _count_via_entity_type_index_optimized(
        self,
        filter_expression: Optional[str],
        expression_values: Dict[str, Any],
        expression_names: Dict[str, str],
        device_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        try:
            count = 0
            last_key = None
            scanned_count = 0

            while True:
                query_result = await self.dynamo_client.query_with_pagination(
                    key_name="entity_type",
                    key_value="COMBINED_RESULT",
                    index_name="EntityTypeIndex",
                    limit=self.max_scan_limit,
                    last_evaluated_key=last_key,
                    scan_index_forward=False,
                    filter_expression=filter_expression,
                    expression_values=expression_values if expression_values else None,
                    expression_names=expression_names if expression_names else None,
                )

                items = query_result.get("items", [])
                scanned_count += query_result.get("scanned_count", 0)

                if device_id:
                    for item in items:
                        if self._matches_device_id(item, device_id):
                            count += 1
                else:
                    count += len(items)

                last_key = query_result.get("last_evaluated_key")
                if not last_key:
                    break

                if count % 1000 == 0 and count > 0:
                    logger.info(f"Contagem em progresso: {count} itens")

            logger.info(f"Contagem finalizada: {count} resultados (scanned: {scanned_count})")
            return {"total_count": count, "scanned_count": scanned_count}

        except Exception as e:
            logger.exception(f"Erro ao contar via entity type index otimizado: {e}")
            raise

    async def _count_via_user_index_optimized(
        self,
        user_id: str,
        filter_expression: Optional[str],
        expression_values: Dict[str, Any],
        expression_names: Dict[str, str],
        device_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        try:
            count = 0
            last_key = None

            while True:
                query_result = await self.dynamo_client.query_with_pagination(
                    key_name="user_id",
                    key_value=user_id,
                    index_name="UserIdIndex",
                    limit=self.max_scan_limit,
                    last_evaluated_key=last_key,
                    scan_index_forward=False,
                    filter_expression=filter_expression,
                    expression_values=expression_values if expression_values else None,
                    expression_names=expression_names if expression_names else None,
                )

                items = query_result.get("items", [])

                if device_id:
                    for item in items:
                        if self._matches_device_id(item, device_id):
                            count += 1
                else:
                    count += len(items)

                last_key = query_result.get("last_evaluated_key")
                if not last_key:
                    break

            logger.info(f"Contagem via UserIdIndex: {count} resultados")
            return {"total_count": count}

        except Exception as e:
            logger.exception(f"Erro ao contar via user index otimizado: {e}")
            raise

    async def get_all_results_cursor_based(
        self,
        limit: int = 20,
        cursor: Optional[str] = None,
        status_filter: Optional[str] = None,
        user_id: Optional[str] = None,
        device_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        exclude_errors: bool = False,
    ) -> Dict[str, Any]:
        try:
            import base64
            import json

            logger.info(f"Cursor-based query: limit={limit}, cursor={cursor}, user={user_id}")

            last_evaluated_key = None
            if cursor:
                try:
                    decoded = base64.b64decode(cursor).decode()
                    last_evaluated_key = json.loads(decoded)
                except Exception as e:
                    logger.warning(f"Invalid cursor: {e}")

            filter_parts = []
            expression_values = {}
            expression_names = {}

            if status_filter:
                filter_parts.append("#status = :status")
                expression_values[":status"] = status_filter
                expression_names["#status"] = "status"

            if exclude_errors:
                filter_parts.append("#status <> :error_status")
                filter_parts.append("#status <> :failed_status")
                expression_values[":error_status"] = "error"
                expression_values[":failed_status"] = "failed"
                expression_names["#status"] = "status"

            if start_date:
                filter_parts.append("created_at >= :start_date")
                expression_values[":start_date"] = start_date.isoformat()

            if end_date:
                filter_parts.append("created_at <= :end_date")
                expression_values[":end_date"] = end_date.isoformat()

            filter_expression = " AND ".join(filter_parts) if filter_parts else None

            if user_id:
                query_result = await self.dynamo_client.query_with_pagination(
                    key_name="user_id",
                    key_value=user_id,
                    index_name="UserIdIndex",
                    limit=limit,
                    last_evaluated_key=last_evaluated_key,
                    scan_index_forward=False,
                    filter_expression=filter_expression,
                    expression_values=expression_values if expression_values else None,
                    expression_names=expression_names if expression_names else None,
                )
            else:
                query_result = await self.dynamo_client.query_with_pagination(
                    key_name="entity_type",
                    key_value="COMBINED_RESULT",
                    index_name="EntityTypeIndex",
                    limit=limit,
                    last_evaluated_key=last_evaluated_key,
                    scan_index_forward=False,
                    filter_expression=filter_expression,
                    expression_values=expression_values if expression_values else None,
                    expression_names=expression_names if expression_names else None,
                )

            items = query_result.get("items", [])

            if device_id:
                items = [item for item in items if self._matches_device_id(item, device_id)]

            formatted_items = [self._format_result_item(item) for item in items]

            next_cursor = None
            if query_result.get("last_evaluated_key"):
                next_key_json = json.dumps(query_result["last_evaluated_key"])
                next_cursor = base64.b64encode(next_key_json.encode()).decode()

            return {
                "items": formatted_items,
                "next_cursor": next_cursor,
                "has_more": next_cursor is not None,
            }

        except Exception as e:
            logger.exception(f"Erro ao buscar resultados cursor-based: {e}")
            raise
