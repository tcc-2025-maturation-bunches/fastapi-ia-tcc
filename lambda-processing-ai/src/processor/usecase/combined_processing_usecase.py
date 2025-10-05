import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fruit_detection_shared.domain.entities import Image
from fruit_detection_shared.infra.external import SNSClient
from fruit_detection_shared.mappers import RequestSummaryMapper

from src.app.config import settings
from src.processor.repository.dynamo_repository import DynamoRepository
from src.processor.repository.ia_repository import IARepository

logger = logging.getLogger(__name__)


class CombinedProcessingUseCase:
    def __init__(self, ia_repository: IARepository, dynamo_repository: DynamoRepository):
        self.ia_repository = ia_repository
        self.dynamo_repository = dynamo_repository
        self.sns_client = SNSClient(region=settings.AWS_REGION)

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

            await self._notify_device_management(
                request_id=request_id,
                device_id=metadata.get("device_id"),
                processing_result=combined_result,
                metadata=metadata,
            )

            logger.info(f"Processamento combinado concluído: {request_id}")

            return combined_result

        except Exception as e:
            logger.exception(f"Erro no processamento combinado: {e}")

            await self._update_status(request_id, "error", 1.0, error=str(e), error_code="PROCESSING_ERROR")

            await self._notify_device_management(
                request_id=request_id,
                device_id=metadata.get("device_id"),
                processing_result=None,
                metadata=metadata,
                error=str(e),
            )

            raise

    async def _notify_device_management(
        self,
        request_id: str,
        device_id: Optional[str],
        processing_result: Optional[Any],
        metadata: Dict[str, Any],
        error: Optional[str] = None,
    ):
        try:
            if not device_id:
                logger.debug(f"Nenhum device_id fornecido para request_id {request_id}, pulando notificação")
                return

            notification_payload = {
                "event_type": "processing_complete",
                "request_id": request_id,
                "device_id": device_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "metadata": {
                    "user_id": metadata.get("user_id"),
                    "image_id": metadata.get("image_id"),
                    "location": metadata.get("location"),
                },
            }

            if error:
                notification_payload.update(
                    {
                        "status": "error",
                        "error_message": error,
                        "processing_result": {"success": False, "processing_time_ms": 0},
                    }
                )
            else:
                success = processing_result and processing_result.status == "success"
                notification_payload.update(
                    {
                        "status": "success" if success else "error",
                        "processing_result": {
                            "success": success,
                            "processing_time_ms": getattr(processing_result, "processing_time_ms", 0),
                            "detection_count": (
                                len(processing_result.detection.results)
                                if processing_result and processing_result.detection
                                else 0
                            ),
                        },
                    }
                )

            topic_arn = settings.SNS_DEVICE_MANAGEMENT_TOPIC
            if topic_arn:
                message_id = self.sns_client.publish_message(
                    topic_arn=topic_arn,
                    message=notification_payload,
                    subject=f"Processing Complete - Device {device_id}",
                    message_attributes={
                        "event_type": {"DataType": "String", "StringValue": "processing_complete"},
                        "device_id": {"DataType": "String", "StringValue": device_id},
                    },
                )
                logger.info(f"Notificação SNS enviada para Device Management: {message_id}")
            else:
                logger.warning("SNS_DEVICE_MANAGEMENT_TOPIC não configurado, pulando notificação")

        except Exception as e:
            logger.warning(f"Falha ao notificar Device Management para device {device_id}: {e}")

    async def _update_status(
        self,
        request_id: str,
        status: str,
        progress: float,
        error: Optional[str] = None,
        error_code: Optional[str] = None,
    ):
        try:
            status_data = {"status": status, "progress": progress, "updated_at": datetime.now(timezone.utc).isoformat()}

            if error:
                status_data["error"] = error
                status_data["error_code"] = error_code or "UNKNOWN_ERROR"

            await self.dynamo_repository.update_processing_status(request_id, status_data)

        except Exception as e:
            logger.warning(f"Erro ao atualizar status para {request_id}: {e}")
