import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fruit_detection_shared.domain.entities import CombinedResult

from src.repository.dynamo_repository import DynamoRepository

logger = logging.getLogger(__name__)


class ResultsService:
    def __init__(self, dynamo_repository: Optional[DynamoRepository] = None):
        self.dynamo_repository = dynamo_repository or DynamoRepository()

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

    async def get_all_results(
        self,
        limit: int = 20,
        last_evaluated_key: Optional[Dict[str, Any]] = None,
        status_filter: Optional[str] = None,
        user_id: Optional[str] = None,
        exclude_errors: bool = False,
    ) -> Dict[str, Any]:
        try:
            logger.info(f"Recuperando todos os resultados (limit: {limit})")

            response = await self.dynamo_repository.get_all_results(
                limit=limit,
                last_evaluated_key=last_evaluated_key,
                status_filter=status_filter,
                user_id=user_id,
                exclude_errors=exclude_errors,
            )

            items = response.get("items", [])
            next_key = response.get("last_evaluated_key")

            processed_items = []
            for item in items:
                processed_item = self._process_result_item(item)
                processed_items.append(processed_item)

            logger.info(f"Recuperados {len(processed_items)} resultados")

            return {
                "items": processed_items,
                "next_page_key": next_key,
                "total_count": len(processed_items),
                "has_more": next_key is not None,
                "filters_applied": {
                    "status_filter": status_filter,
                    "user_id": user_id,
                    "exclude_errors": exclude_errors,
                },
            }

        except Exception as e:
            logger.exception(f"Erro ao recuperar todos os resultados: {e}")
            raise

    async def get_results_summary(self, days: int = 7) -> Dict[str, Any]:
        try:
            logger.info(f"Gerando resumo dos resultados dos últimos {days} dias")

            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

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
        processed_item = {
            "request_id": item.get("request_id"),
            "image_id": item.get("image_id"),
            "user_id": item.get("user_id"),
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
