import logging
from typing import Any, Dict, List, Optional

from src.modules.storage.repo.dynamo_repository import DynamoRepository
from src.shared.domain.entities.result import ProcessingResult

logger = logging.getLogger(__name__)


class GetResultUseCase:
    def __init__(self, dynamo_repository: Optional[DynamoRepository] = None):
        self.dynamo_repository = dynamo_repository or DynamoRepository()

    async def get_by_request_id(self, request_id: str) -> Optional[ProcessingResult]:
        """Recupera resultado por request_id."""
        try:
            logger.info(f"Recuperando resultado para request_id: {request_id}")
            return await self.dynamo_repository.get_result_by_request_id(request_id)
        except Exception as e:
            logger.exception(f"Erro ao recuperar resultado por request_id: {e}")
            raise

    async def get_by_image_id(self, image_id: str) -> List[ProcessingResult]:
        """Recupera todos os resultados para uma imagem."""
        try:
            logger.info(f"Recuperando resultados para image_id: {image_id}")
            return await self.dynamo_repository.get_results_by_image_id(image_id)
        except Exception as e:
            logger.exception(f"Erro ao recuperar resultados por image_id: {e}")
            raise

    async def get_by_user_id(self, user_id: str, limit: int = 10) -> List[ProcessingResult]:
        """Recupera resultados por user_id."""
        try:
            logger.info(f"Recuperando resultados para user_id: {user_id}")
            return await self.dynamo_repository.get_results_by_user_id(user_id, limit)
        except Exception as e:
            logger.exception(f"Erro ao recuperar resultados por user_id: {e}")
            raise

    async def get_all_results(
        self, limit: int = 50, last_evaluated_key: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Recupera todos os resultados de inferência de IA usando o GSI EntityTypeIndex.

        Esta função busca tanto resultados do tipo RESULT quanto COMBINED_RESULT,
        implementando paginação eficiente para evitar scans custosos.

        Args:
            limit: Número máximo de resultados a retornar
            last_evaluated_key: Chave para continuar paginação

        Returns:
            Dict contendo:
            - items: Lista de resultados de inferência
            - last_evaluated_key: Chave para próxima página (se houver)
        """
        try:
            logger.info(f"Recuperando todos os resultados de inferência (limit: {limit})")

            response = await self.dynamo_repository.get_all_results(limit=limit, last_evaluated_key=last_evaluated_key)

            items = response.get("items", [])
            next_key = response.get("last_evaluated_key")

            result_types = {}
            for item in items:
                entity_type = item.get("entity_type", "unknown")
                result_types[entity_type] = result_types.get(entity_type, 0) + 1

            logger.info(f"Recuperados {len(items)} resultados: {result_types}")

            return {"items": items, "last_evaluated_key": next_key}

        except Exception as e:
            logger.exception(f"Erro ao recuperar todos os resultados de inferência: {e}")
            raise

    async def get_results_summary(self, days: int = 7) -> Dict[str, Any]:
        """
        Recupera um resumo dos resultados de inferência dos últimos N dias.

        Args:
            days: Número de dias para incluir no resumo

        Returns:
            Dict com estatísticas resumidas dos resultados
        """
        try:
            from datetime import datetime, timedelta, timezone

            logger.info(f"Gerando resumo dos resultados dos últimos {days} dias")

            response = await self.get_all_results(limit=200)
            items = response.get("items", [])

            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            recent_items = []

            for item in items:
                created_at = item.get("createdAt")
                if created_at:
                    try:
                        created_dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                        if created_dt >= cutoff_date:
                            recent_items.append(item)
                    except ValueError:
                        continue

            total_results = len(recent_items)

            by_type = {}
            by_status = {}
            by_user = {}

            successful_results = 0
            failed_results = 0
            total_processing_time = 0
            processing_count = 0

            for item in recent_items:
                entity_type = item.get("entity_type", "unknown")
                by_type[entity_type] = by_type.get(entity_type, 0) + 1

                status = item.get("status", "unknown")
                by_status[status] = by_status.get(status, 0) + 1

                if status in ["success", "completed"]:
                    successful_results += 1
                elif status in ["error", "failed"]:
                    failed_results += 1

                user_id = item.get("user_id", "unknown")
                by_user[user_id] = by_user.get(user_id, 0) + 1
                processing_time = item.get("processing_time_ms", 0)
                if processing_time > 0:
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
                "results_by_type": by_type,
                "results_by_status": by_status,
                "top_users": [{"user_id": user, "count": count} for user, count in top_users],
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }

            logger.info(f"Resumo gerado: {total_results} resultados, {success_rate:.1f}% sucesso")
            return summary

        except Exception as e:
            logger.exception(f"Erro ao gerar resumo dos resultados: {e}")
            raise

    async def search_results(
        self,
        user_id: Optional[str] = None,
        status: Optional[str] = None,
        entity_type: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Busca resultados com filtros específicos.

        Args:
            user_id: Filtrar por usuário específico
            status: Filtrar por status (success, error, etc.)
            entity_type: Filtrar por tipo (RESULT, COMBINED_RESULT)
            limit: Número máximo de resultados

        Returns:
            Lista de resultados que atendem aos critérios
        """
        try:
            logger.info(f"Buscando resultados - user_id: {user_id}, status: {status}, type: {entity_type}")

            response = await self.get_all_results(limit=limit * 2)
            items = response.get("items", [])

            filtered_items = []
            for item in items:
                if user_id and item.get("user_id") != user_id:
                    continue

                if status and item.get("status") != status:
                    continue

                if entity_type and item.get("entity_type") != entity_type:
                    continue

                filtered_items.append(item)

                if len(filtered_items) >= limit:
                    break

            logger.info(f"Retornando {len(filtered_items)} resultados filtrados")
            return filtered_items

        except Exception as e:
            logger.exception(f"Erro ao buscar resultados com filtros: {e}")
            raise
