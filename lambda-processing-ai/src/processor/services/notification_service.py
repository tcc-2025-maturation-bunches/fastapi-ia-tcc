import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fruit_detection_shared.domain.entities import CombinedResult
from fruit_detection_shared.infra.external import SNSClient

from src.app.config import settings

logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(self, sns_client: Optional[SNSClient] = None):
        self.sns_client = sns_client or SNSClient(region=settings.AWS_REGION)
        self.topic_arn = settings.SNS_DEVICE_MANAGEMENT_TOPIC

    async def notify_processing_complete(
        self,
        request_id: str,
        device_id: Optional[str],
        processing_result: CombinedResult,
        user_id: str,
        image_id: str,
        location: Optional[str] = None,
    ) -> bool:
        if not device_id:
            logger.debug(f"Nenhum device_id fornecido para request_id {request_id}")
            return False

        payload = self._build_completion_payload(
            request_id=request_id,
            device_id=device_id,
            processing_result=processing_result,
            user_id=user_id,
            image_id=image_id,
            location=location,
        )

        return await self._send_notification(payload, device_id, "processing_complete")

    async def notify_processing_failed(
        self,
        request_id: str,
        device_id: Optional[str],
        error_message: str,
        error_code: str,
        user_id: str,
        image_id: str,
    ) -> bool:
        if not device_id:
            logger.debug(f"Nenhum device_id fornecido para request_id {request_id}")
            return False

        payload = self._build_failure_payload(
            request_id=request_id,
            device_id=device_id,
            error_message=error_message,
            error_code=error_code,
            user_id=user_id,
            image_id=image_id,
        )

        return await self._send_notification(payload, device_id, "processing_failed")

    async def _send_notification(
        self,
        payload: Dict[str, Any],
        device_id: str,
        event_type: str,
    ) -> bool:
        if not self.topic_arn:
            logger.warning("SNS_DEVICE_MANAGEMENT_TOPIC não configurado")
            return False

        try:
            message_id = self.sns_client.publish_message(
                topic_arn=self.topic_arn,
                message=payload,
                subject=f"Processing Notification - Device {device_id}",
                message_attributes={
                    "event_type": {"DataType": "String", "StringValue": event_type},
                    "device_id": {"DataType": "String", "StringValue": device_id},
                },
            )
            logger.info(f"Notificação SNS enviada: {message_id}")
            return True

        except Exception as e:
            logger.warning(f"Falha ao enviar notificação SNS: {e}")
            return False

    def _build_completion_payload(
        self,
        request_id: str,
        device_id: str,
        processing_result: CombinedResult,
        user_id: str,
        image_id: str,
        location: Optional[str],
    ) -> Dict[str, Any]:
        success = processing_result and processing_result.status == "success"

        return {
            "event_type": "processing_complete",
            "request_id": request_id,
            "device_id": device_id,
            "status": "success" if success else "error",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metadata": {
                "user_id": user_id,
                "image_id": image_id,
                "location": location,
            },
            "processing_result": {
                "success": success,
                "processing_time_ms": getattr(processing_result, "processing_time_ms", 0),
                "detection_count": (
                    len(processing_result.detection.results) if processing_result and processing_result.detection else 0
                ),
            },
        }

    def _build_failure_payload(
        self,
        request_id: str,
        device_id: str,
        error_message: str,
        error_code: str,
        user_id: str,
        image_id: str,
    ) -> Dict[str, Any]:
        return {
            "event_type": "processing_failed",
            "request_id": request_id,
            "device_id": device_id,
            "status": "error",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metadata": {
                "user_id": user_id,
                "image_id": image_id,
            },
            "error": {
                "error_code": error_code,
                "error_message": error_message,
            },
            "processing_result": {
                "success": False,
                "processing_time_ms": 0,
            },
        }
