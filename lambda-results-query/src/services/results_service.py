import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fruit_detection_shared.domain.entities import CombinedResult

from src.app.config import settings
from src.models.stats_models import (
    InferenceStatsResponse,
    LocationCountItem,
    LocationDailyItem,
    MaturationDistributionItem,
    MaturationTrendItem,
)
from src.repository.dynamo_repository import DynamoRepository
from src.services.cache_service import CacheService

logger = logging.getLogger(__name__)


class ResultsService:
    def __init__(
        self, dynamo_repository: Optional[DynamoRepository] = None, cache_service: Optional[CacheService] = None
    ):
        self.dynamo_repository = dynamo_repository or DynamoRepository()
        if cache_service is None:
            cache_service = CacheService(ttl_seconds=settings.CACHE_TTL_SECONDS)
        self.cache_service = cache_service

    async def get_by_request_id(self, request_id: str) -> Optional[Dict[str, Any]]:
        try:
            logger.info(f"Recuperando resultado para request_id: {request_id}")
            return await self.dynamo_repository.get_result_by_request_id(request_id)
        except Exception as e:
            logger.exception(f"Erro ao recuperar resultado por request_id: {e}")
            raise

    async def get_by_image_id(self, image_id: str) -> List[Dict[str, Any]]:
        try:
            logger.info(f"Recuperando resultados para image_id: {image_id}")
            return await self.dynamo_repository.get_results_by_image_id(image_id)
        except Exception as e:
            logger.exception(f"Erro ao recuperar resultados por image_id: {e}")
            raise

    async def get_by_user_id(self, user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        try:
            logger.info(f"Recuperando resultados para user_id: {user_id}")
            return await self.dynamo_repository.get_results_by_user_id(user_id, limit)
        except Exception as e:
            logger.exception(f"Erro ao recuperar resultados por user_id: {e}")
            raise

    async def get_by_device_id(self, device_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        try:
            logger.info(f"Recuperando resultados para device_id: {device_id}")
            return await self.dynamo_repository.get_results_by_device_id(device_id, limit)
        except Exception as e:
            logger.exception(f"Erro ao recuperar resultados por device_id: {e}")
            raise

    async def get_all_results(
        self,
        page: int = 1,
        page_size: int = 20,
        status_filter: Optional[str] = None,
        user_id: Optional[str] = None,
        device_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        exclude_errors: bool = False,
    ) -> Dict[str, Any]:
        try:
            logger.info(f"Recuperando página {page} com {page_size} itens por página")

            if page < 1:
                page = 1
            if page_size < 1:
                page_size = 20

            cache_key_params = {
                "status": status_filter,
                "user": user_id,
                "device": device_id,
                "start": start_date.isoformat() if start_date else None,
                "end": end_date.isoformat() if end_date else None,
                "exclude_err": exclude_errors,
            }

            cached_count = await self.cache_service.get("count", **cache_key_params)
            if cached_count is not None:
                logger.info(f"Usando contagem em cache: {cached_count}")
                total_count = cached_count
            else:
                total_count_result = await self.dynamo_repository.count_all_results_optimized(
                    status_filter=status_filter,
                    user_id=user_id,
                    device_id=device_id,
                    start_date=start_date,
                    end_date=end_date,
                    exclude_errors=exclude_errors,
                )
                total_count = total_count_result.get("total_count", 0)
                await self.cache_service.set(
                    "count", total_count, ttl_seconds=settings.CACHE_COUNT_TTL_SECONDS, **cache_key_params
                )

            total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 1

            if page > total_pages:
                page = total_pages

            offset = (page - 1) * page_size

            response = await self.dynamo_repository.get_all_results_with_offset(
                offset=offset,
                limit=page_size,
                status_filter=status_filter,
                user_id=user_id,
                device_id=device_id,
                start_date=start_date,
                end_date=end_date,
                exclude_errors=exclude_errors,
            )

            items = response.get("items", [])

            processed_items = [self._process_result_item(item) for item in items]

            logger.info(
                f"Página {page}/{total_pages} recuperada com {len(processed_items)} itens " f"(total: {total_count})"
            )

            return {
                "items": processed_items,
                "total_count": total_count,
                "total_pages": total_pages,
                "current_page": page,
                "page_size": page_size,
                "has_previous": page > 1,
                "has_next": page < total_pages,
                "filters_applied": {
                    "status_filter": status_filter,
                    "user_id": user_id,
                    "device_id": device_id,
                    "start_date": start_date.isoformat() if start_date is not None else None,
                    "end_date": end_date.isoformat() if end_date is not None else None,
                    "exclude_errors": exclude_errors,
                },
            }

        except Exception as e:
            logger.exception(f"Erro ao recuperar resultados paginados: {e}")
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
            logger.info(f"Paginação baseada em cursor: limit={limit}, cursor={'presente' if cursor else 'nenhum'}")

            response = await self.dynamo_repository.get_all_results_cursor_based(
                limit=limit,
                cursor=cursor,
                status_filter=status_filter,
                user_id=user_id,
                device_id=device_id,
                start_date=start_date,
                end_date=end_date,
                exclude_errors=exclude_errors,
            )

            items = response.get("items", [])
            processed_items = [self._process_result_item(item) for item in items]

            result = {
                "items": processed_items,
                "next_cursor": response.get("next_cursor"),
                "has_more": response.get("has_more", False),
                "count": len(processed_items),
                "filters_applied": {
                    "status_filter": status_filter,
                    "user_id": user_id,
                    "device_id": device_id,
                    "start_date": start_date.isoformat() if start_date else None,
                    "end_date": end_date.isoformat() if end_date else None,
                    "exclude_errors": exclude_errors,
                },
            }

            logger.info(f"Query cursor-based retornou {len(processed_items)} itens")
            return result

        except Exception as e:
            logger.exception(f"Erro ao recuperar resultados cursor-based: {e}")
            raise

    async def get_results_summary(self, days: int = 7, device_id: Optional[str] = None) -> Dict[str, Any]:
        try:
            logger.info(f"Gerando resumo dos resultados dos últimos {days} dias")
            if device_id:
                logger.info(f"Filtrado por device_id: {device_id}")

            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

            if device_id:
                response = await self.dynamo_repository.get_results_with_filters(
                    start_date=cutoff_date, limit=1000, device_id=device_id
                )
            else:
                response = await self.dynamo_repository.get_results_with_filters(start_date=cutoff_date, limit=1000)

            items = response.get("items", [])

            total_results = len(items)
            by_status = {}
            by_user = {}
            successful_results = 0
            failed_results = 0
            total_processing_time = 0
            processing_count = 0

            for item in items:
                status = item.get("status", "unknown")
                by_status[status] = by_status.get(status, 0) + 1

                if status in ["success", "completed"]:
                    successful_results += 1
                elif status in ["error", "failed"]:
                    failed_results += 1

                user_id = item.get("user_id", "unknown")
                by_user[user_id] = by_user.get(user_id, 0) + 1

                processing_time = item.get("processing_time_ms", 0)
                if processing_time and processing_time > 0:
                    total_processing_time += processing_time
                    processing_count += 1

            success_rate = 0.0
            if total_results > 0:
                success_rate = (successful_results / total_results) * 100

            avg_processing_time = 0.0
            if processing_count > 0:
                avg_processing_time = total_processing_time / processing_count

            top_users = sorted(by_user.items(), key=lambda x: x[1], reverse=True)[:5]

            summary = {
                "period_days": days,
                "device_id": device_id,
                "total_results": total_results,
                "successful_results": successful_results,
                "failed_results": failed_results,
                "success_rate": round(success_rate, 2),
                "average_processing_time_ms": round(avg_processing_time, 2),
                "results_by_status": by_status,
                "top_users": [{"user_id": user, "count": count} for user, count in top_users],
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }

            logger.info(f"Resumo gerado: {total_results} resultados, {success_rate:.1f}% sucesso")
            return summary

        except Exception as e:
            logger.exception(f"Erro ao gerar resumo dos resultados: {e}")
            raise

    async def get_user_statistics(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        try:
            logger.info(f"Gerando estatísticas para usuário {user_id} ({days} dias)")

            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

            results = await self.dynamo_repository.get_results_by_user_id(user_id, limit=500)

            recent_results = []
            for result in results:
                created_at = result.get("created_at")
                if created_at:
                    try:
                        created_dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                        if created_dt >= cutoff_date:
                            recent_results.append(result)
                    except ValueError:
                        continue

            total_results = len(recent_results)
            successful = sum(1 for r in recent_results if r.get("status") in ["success", "completed"])
            failed = sum(1 for r in recent_results if r.get("status") in ["error", "failed"])

            success_rate = 0.0
            if total_results > 0:
                success_rate = (successful / total_results) * 100

            processing_times = [
                r.get("processing_time_ms", 0)
                for r in recent_results
                if r.get("processing_time_ms") and r.get("processing_time_ms") > 0
            ]

            avg_processing_time = 0.0
            if processing_times:
                avg_processing_time = sum(processing_times) / len(processing_times)

            last_activity = None
            if recent_results:
                sorted_results = sorted(recent_results, key=lambda x: x.get("created_at", ""), reverse=True)
                last_activity = sorted_results[0].get("created_at")

            daily_counts = self._calculate_daily_activity(recent_results, days)

            stats = {
                "user_id": user_id,
                "period_days": days,
                "total_results": total_results,
                "successful_results": successful,
                "failed_results": failed,
                "success_rate": round(success_rate, 2),
                "average_processing_time_ms": round(avg_processing_time, 2),
                "last_activity": last_activity,
                "daily_activity": daily_counts,
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }

            return stats

        except Exception as e:
            logger.exception(f"Erro ao gerar estatísticas do usuário: {e}")
            raise

    def _convert_to_combined_result(self, item: Dict[str, Any]) -> Optional[CombinedResult]:
        try:
            if not item:
                return None
            return CombinedResult.from_dict(item)
        except Exception as e:
            logger.warning(f"Erro ao converter item para CombinedResult: {e}")
            return None

    def _process_result_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        initial_metadata = item.get("initial_metadata", {})
        location = initial_metadata.get("location") if initial_metadata else None

        processed_item = {
            "request_id": item.get("request_id"),
            "image_id": item.get("image_id"),
            "user_id": item.get("user_id"),
            "location": location,
            "status": item.get("status"),
            "created_at": item.get("created_at"),
            "updated_at": item.get("updated_at"),
            "processing_time_ms": item.get("processing_time_ms"),
            "image_url": item.get("image_url"),
            "image_result_url": item.get("image_result_url"),
        }

        if item.get("detection_result"):
            processed_item["detection_results"] = item["detection_result"]

        if item.get("processing_metadata"):
            processed_item["processing_metadata"] = item["processing_metadata"]

        if item.get("error_info"):
            processed_item["error_info"] = item["error_info"]

        return processed_item

    def _calculate_daily_activity(self, results: List[Dict[str, Any]], days: int) -> List[Dict[str, Any]]:
        daily_counts = []

        for i in range(days):
            day_start = datetime.now(timezone.utc) - timedelta(days=i + 1)
            day_end = day_start + timedelta(days=1)

            day_results = []
            for result in results:
                created_at = result.get("created_at")
                if created_at:
                    try:
                        created_dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                        if day_start <= created_dt < day_end:
                            day_results.append(result)
                    except ValueError:
                        continue

            successful = sum(1 for r in day_results if r.get("status") in ["success", "completed"])
            failed = sum(1 for r in day_results if r.get("status") in ["error", "failed"])

            daily_counts.append(
                {
                    "date": day_start.strftime("%Y-%m-%d"),
                    "total": len(day_results),
                    "successful": successful,
                    "failed": failed,
                }
            )

        return list(reversed(daily_counts))

    async def get_inference_stats(self, days: int = 7) -> Dict[str, Any]:
        try:
            logger.info(f"Gerando estatísticas de inferência dos últimos {days} dias")

            cache_params = {"days": days}
            cached_stats = await self.cache_service.get("inference_stats", **cache_params)
            if cached_stats is not None:
                logger.info("Retornando estatísticas de inferência em cache")
                return cached_stats

            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            response = await self.dynamo_repository.get_results_with_filters(
                start_date=cutoff_date, status_filter="success", limit=2000
            )

            items = response.get("items", [])
            total_inspections = len(items)

            MATURATION_KEYS = ["verde", "quase_maduro", "maduro", "muito_maduro_ou_passado"]

            maturation_counts = {key: 0 for key in MATURATION_KEYS}
            trend_data: Dict[str, Dict[str, int]] = {}
            location_data: Dict[str, Dict[str, int]] = {}
            location_daily_data: Dict[str, Dict[str, Dict[str, int]]] = {}
            total_objects = 0

            for item in items:
                created_at_str = item.get("created_at")
                day_str = "Unknown"
                if created_at_str:
                    try:
                        created_dt = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
                        day_str = created_dt.strftime("%d/%m")
                    except ValueError:
                        logger.warning(f"Formato de data inválido encontrado: {created_at_str}")

                location = item.get("initial_metadata", {}).get("location", "Desconhecido")
                if location not in location_data:
                    location_data[location] = {"count": 0, **{k: 0 for k in MATURATION_KEYS}}
                    location_daily_data[location] = {}
                location_data[location]["count"] += 1

                maturation_distribution = {}
                processing_metadata = item.get("processing_metadata")
                if processing_metadata and isinstance(processing_metadata, dict):
                    maturation_distribution = processing_metadata.get("maturation_distribution", {})
                if not maturation_distribution:
                    detection_result = item.get("detection_result", {})
                    summary = detection_result.get("summary", {})
                    maturation_distribution = summary.get("maturation_counts", {})

                if not maturation_distribution or not isinstance(maturation_distribution, dict):
                    continue

                item_total_count = 0
                for key in MATURATION_KEYS:
                    count = maturation_distribution.get(key, 0)
                    maturation_counts[key] += count
                    location_data[location][key] += count
                    total_objects += count
                    item_total_count += count

                    if day_str != "Unknown":
                        if day_str not in trend_data:
                            trend_data[day_str] = {k: 0 for k in MATURATION_KEYS}
                            trend_data[day_str]["total"] = 0
                        trend_data[day_str][key] += count

                        if day_str not in location_daily_data[location]:
                            location_daily_data[location][day_str] = {k: 0 for k in MATURATION_KEYS}
                            location_daily_data[location][day_str]["total"] = 0
                        location_daily_data[location][day_str][key] += count

                if day_str != "Unknown":
                    trend_data[day_str]["total"] += item_total_count
                    location_daily_data[location][day_str]["total"] += item_total_count

            maturation_distribution = [
                MaturationDistributionItem(key=key, value=maturation_counts[key]) for key in MATURATION_KEYS
            ]

            maturation_trend = [MaturationTrendItem(date=day, **counts) for day, counts in sorted(trend_data.items())]

            counts_by_location = [
                LocationCountItem(
                    location=loc,
                    **{k: counts[k] for k in ["count"] + MATURATION_KEYS},
                    daily_trend=[
                        LocationDailyItem(date=day, **day_counts)
                        for day, day_counts in sorted(location_daily_data[loc].items())
                    ],
                )
                for loc, counts in sorted(location_data.items(), key=lambda item: item[1]["count"], reverse=True)
            ]

            response_model = InferenceStatsResponse(
                period_days=days,
                total_inspections=total_inspections,
                total_objects_detected=total_objects,
                maturation_distribution=maturation_distribution,
                maturation_trend=maturation_trend,
                counts_by_location=counts_by_location,
                generated_at=datetime.now(timezone.utc).isoformat(),
            )

            result = response_model.model_dump()
            await self.cache_service.set(
                "inference_stats", result, ttl_seconds=settings.CACHE_STATS_TTL_SECONDS, **cache_params
            )

            logger.info(f"Estatísticas de inferência geradas: {total_inspections} inspeções, {total_objects} objetos")
            return result

        except Exception as e:
            logger.exception(f"Erro ao gerar estatísticas de inferência: {e}")
            raise
