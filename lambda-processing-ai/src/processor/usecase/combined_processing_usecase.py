import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fruit_detection_shared.domain.entities import CombinedResult, Image
from fruit_detection_shared.mappers import RequestSummaryMapper

from src.processor.repository.dynamo_repository import DynamoRepository
from src.processor.services.ia_service import IAService
from src.processor.services.notification_service import NotificationService
from src.processor.services.status_service import ProcessingStage, StatusService

logger = logging.getLogger(__name__)


class CombinedProcessingUseCase:
    def __init__(
        self,
        ia_service: IAService,
        status_service: StatusService,
        notification_service: NotificationService,
        dynamo_repository: DynamoRepository,
    ):
        self.ia_service = ia_service
        self.status_service = status_service
        self.notification_service = notification_service
        self.dynamo_repository = dynamo_repository

    async def execute_processing(
        self,
        request_id: str,
        image_url: str,
        user_id: str,
        result_upload_url: Optional[str],
        metadata: Dict[str, Any],
        maturation_threshold: float = 0.6,
    ) -> CombinedResult:
        device_id = metadata.get("device_id")
        image_id = metadata.get("image_id")
        location = metadata.get("location")

        try:
            await self.status_service.update_stage(request_id, ProcessingStage.PROCESSING)

            image = self._create_image_entity(image_url, user_id, metadata, image_id)

            await self.status_service.update_stage(request_id, ProcessingStage.PROCESSING_AI)

            combined_result = await self.ia_service.process_image(
                image=image,
                result_upload_url=result_upload_url,
                maturation_threshold=maturation_threshold,
            )

            if combined_result.status == "error":
                await self._handle_processing_error(
                    request_id=request_id,
                    error_result=combined_result,
                    device_id=device_id,
                    user_id=user_id,
                    image_id=image_id,
                )
                return combined_result

            await self.status_service.update_stage(request_id, ProcessingStage.SAVING_RESULTS)

            await self._save_results(
                user_id=user_id,
                request_id=request_id,
                metadata=metadata,
                image_url=image_url,
                combined_result=combined_result,
            )

            await self.status_service.mark_as_completed(
                request_id=request_id,
                processing_time_ms=combined_result.processing_time_ms,
                result_url=combined_result.image_result_url,
            )

            await self.notification_service.notify_processing_complete(
                request_id=request_id,
                device_id=device_id,
                processing_result=combined_result,
                user_id=user_id,
                image_id=image_id,
                location=location,
            )

            logger.info(f"Processamento concluído com sucesso: {request_id}")
            return combined_result

        except Exception as e:
            logger.exception(f"Erro no processamento combinado: {e}")

            await self._handle_processing_error(
                request_id=request_id,
                error_result=CombinedResult(
                    status="error",
                    error_message=str(e),
                    error_code="PROCESSING_ERROR",
                ),
                device_id=device_id,
                user_id=user_id,
                image_id=image_id,
            )

            raise

    async def _save_results(
        self,
        user_id: str,
        request_id: str,
        metadata: Dict[str, Any],
        image_url: str,
        combined_result: CombinedResult,
    ) -> None:
        full_metadata = metadata.copy()
        full_metadata["image_url"] = image_url
        full_metadata["image_id"] = metadata.get("image_id")

        if "timestamp" not in full_metadata:
            full_metadata["timestamp"] = datetime.now(timezone.utc).isoformat()

        dynamo_item = RequestSummaryMapper.to_dynamo_item(
            user_id=user_id,
            request_id=request_id,
            initial_metadata=full_metadata,
            combined_result=combined_result,
        )

        await self.dynamo_repository.put_item(dynamo_item)
        logger.info(f"Resultados salvos no DynamoDB: {request_id}")

    async def _handle_processing_error(
        self,
        request_id: str,
        error_result: CombinedResult,
        device_id: Optional[str],
        user_id: str,
        image_id: str,
    ) -> None:
        error_message = error_result.error_message or "Erro desconhecido"
        error_code = error_result.error_code or "UNKNOWN_ERROR"

        await self.status_service.mark_as_failed(
            request_id=request_id,
            error_message=error_message,
            error_code=error_code,
            error_details=error_result.error_details,
        )

        await self.notification_service.notify_processing_failed(
            request_id=request_id,
            device_id=device_id,
            error_message=error_message,
            error_code=error_code,
            user_id=user_id,
            image_id=image_id,
        )

    def _create_image_entity(
        self,
        image_url: str,
        user_id: str,
        metadata: Dict[str, Any],
        image_id: Optional[str],
    ) -> Image:
        return Image(
            image_url=image_url,
            user_id=user_id,
            metadata=metadata,
            image_id=image_id,
        )
