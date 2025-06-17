import logging
from datetime import datetime
from typing import Any, Dict, Optional

from src.modules.storage.repo.dynamo_repository import DynamoRepository

logger = logging.getLogger(__name__)


class GetResultUseCase:
    def __init__(self, dynamo_repository: Optional[DynamoRepository] = None):
        self.dynamo_repository = dynamo_repository or DynamoRepository()

    async def get_all_results_with_filters(
        self,
        user_id: Optional[str] = None,
        status: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 50,
        last_evaluated_key: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        try:
            logger.info(
                f"Recuperando resultados com filtros - user_id: {user_id}, "
                f"status: {status}, dates: {start_date} to {end_date}"
            )

            response = await self.dynamo_repository.query_results_with_filters(
                user_id=user_id,
                status=status,
                start_date=start_date,
                end_date=end_date,
                limit=limit,
                last_evaluated_key=last_evaluated_key,
            )

            items = response.get("items", [])
            next_key = response.get("last_evaluated_key")

            logger.info(f"Recuperados {len(items)} resultados")

            return {"items": items, "last_evaluated_key": next_key}

        except Exception as e:
            logger.exception(f"Erro ao recuperar resultados com filtros: {e}")
            raise
