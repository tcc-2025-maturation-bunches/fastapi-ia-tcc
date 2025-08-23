import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fruit_detection_shared.domain.entities import Image
from fruit_detection_shared.mappers import RequestSummaryMapper

from src.processor.repository.dynamo_repository import DynamoRepository
from src.processor.repository.ia_repository import IARepository

logger = logging.getLogger(__name__)


class CombinedProcessingUseCase:
    def __init__(self, ia_repository: IARepository, dynamo_repository: DynamoRepository):
        self.ia_repository = ia_repository
        self.dynamo_repository = dynamo_repository

    async def execute_processing(
        self,
        request_id: str,
        image_url: str,
        user_id: str,
        result_upload_url: Optional[str],
        metadata: Dict[str, Any],
        maturation_threshold: float = 0.6,
    ) -> Dict[str, Any]:
        try:
            await self._update_status(request_id, "processing", 0.1)

            image = Image(image_url=image_url, user_id=user_id, metadata=metadata, image_id=metadata.get("image_id"))

            await self._update_status(request_id, "processing_ai", 0.3)

            combined_result = await self.ia_repository.process_combined(
                image=image, result_upload_url=result_upload_url, maturation_threshold=maturation_threshold
            )

            await self._update_status(request_id, "saving_results", 0.8)

            full_metadata = metadata.copy()
            full_metadata["image_url"] = image_url
            full_metadata["image_id"] = image.image_id
            if "timestamp" not in full_metadata:
                full_metadata["timestamp"] = datetime.now(timezone.utc).isoformat()

            final_item = RequestSummaryMapper.to_dynamo_item(
                user_id=user_id, request_id=request_id, initial_metadata=full_metadata, combined_result=combined_result
            )

            await self.dynamo_repository.save_request_summary(final_item)

            await self._update_status(request_id, "completed", 1.0)

            logger.info(f"Processamento combinado concluído: {request_id}")

            return combined_result

        except Exception as e:
            logger.exception(f"Erro no processamento combinado: {e}")

            await self._update_status(request_id, "error", 1.0, error=str(e), error_code="PROCESSING_ERROR")

            raise

    async def _update_status(
        self,
        request_id: str,
        status: str,
        progress: float,
        error: Optional[str] = None,
        error_code: Optional[str] = None,
    ):
        try:
            status_data = {"status": status, "progress": progress, "updatedAt": datetime.now(timezone.utc).isoformat()}

            if error:
                status_data["error"] = error
                status_data["error_code"] = error_code or "UNKNOWN_ERROR"

            await self.dynamo_repository.update_processing_status(request_id, status_data)

        except Exception as e:
            logger.warning(f"Erro ao atualizar status para {request_id}: {e}")
