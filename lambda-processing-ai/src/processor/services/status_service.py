import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional

from src.processor.repository.dynamo_repository import DynamoRepository

logger = logging.getLogger(__name__)


class ProcessingStage(Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    PROCESSING_AI = "processing_ai"
    SAVING_RESULTS = "saving_results"
    COMPLETED = "completed"
    ERROR = "error"


class StatusService:
    STAGE_PROGRESS = {
        ProcessingStage.QUEUED: 0.0,
        ProcessingStage.PROCESSING: 0.1,
        ProcessingStage.PROCESSING_AI: 0.3,
        ProcessingStage.SAVING_RESULTS: 0.8,
        ProcessingStage.COMPLETED: 1.0,
        ProcessingStage.ERROR: 1.0,
    }

    def __init__(self, dynamo_repository: DynamoRepository):
        self.dynamo_repository = dynamo_repository

    async def create_initial_status(
        self,
        request_id: str,
        user_id: str,
        image_url: str,
        metadata: Dict[str, Any],
    ) -> None:
        status_data = self._build_status_item(
            request_id=request_id,
            user_id=user_id,
            image_url=image_url,
            metadata=metadata,
            status=ProcessingStage.QUEUED,
        )

        try:
            await self.dynamo_repository.put_item(status_data)
            logger.info(f"Status inicial criado para request_id: {request_id}")
        except Exception as e:
            logger.error(f"Erro ao criar status inicial: {e}")
            raise

    async def update_stage(
        self,
        request_id: str,
        stage: ProcessingStage,
        additional_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        progress = self.STAGE_PROGRESS.get(stage, 0.0)

        status_update = {
            "status": stage.value,
            "progress": progress,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        if additional_data:
            status_update.update(additional_data)

        try:
            await self.dynamo_repository.update_processing_status(request_id, status_update)
            logger.debug(f"Status atualizado para {stage.value}: {request_id}")
        except Exception as e:
            logger.warning(f"Erro ao atualizar status: {e}")

    async def mark_as_completed(
        self,
        request_id: str,
        processing_time_ms: int,
        result_url: Optional[str] = None,
    ) -> None:
        completion_data = {
            "status": ProcessingStage.COMPLETED.value,
            "progress": 1.0,
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "processing_time_ms": processing_time_ms,
        }

        if result_url:
            completion_data["result_url"] = result_url

        try:
            await self.dynamo_repository.update_processing_status(request_id, completion_data)
            logger.info(f"Processamento concluído para request_id: {request_id}")
        except Exception as e:
            logger.error(f"Erro ao marcar como concluído: {e}")

    async def mark_as_failed(
        self,
        request_id: str,
        error_message: str,
        error_code: str = "UNKNOWN_ERROR",
        error_details: Optional[Dict[str, Any]] = None,
    ) -> None:
        failure_data = {
            "status": ProcessingStage.ERROR.value,
            "progress": 1.0,
            "failed_at": datetime.now(timezone.utc).isoformat(),
            "error_message": error_message,
            "error_code": error_code,
        }

        if error_details:
            failure_data["error_details"] = error_details

        try:
            await self.dynamo_repository.update_processing_status(request_id, failure_data)
            logger.error(f"Processamento falhou para request_id: {request_id} - {error_code}")
        except Exception as e:
            logger.error(f"Erro ao marcar como falho: {e}")

    async def get_status(self, request_id: str) -> Optional[Dict[str, Any]]:
        try:
            return await self.dynamo_repository.get_processing_status(request_id)
        except Exception as e:
            logger.error(f"Erro ao recuperar status: {e}")
            return None

    def _build_status_item(
        self,
        request_id: str,
        user_id: str,
        image_url: str,
        metadata: Dict[str, Any],
        status: ProcessingStage,
    ) -> Dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()

        return {
            "pk": f"STATUS#{request_id}",
            "sk": "INFO",
            "entity_type": "PROCESSING_STATUS",
            "request_id": request_id,
            "user_id": user_id,
            "image_url": image_url,
            "status": status.value,
            "progress": self.STAGE_PROGRESS[status],
            "metadata": metadata,
            "created_at": now,
            "updated_at": now,
        }
