import logging
from typing import Any, Dict

from src.processor.repository.dynamo_repository import DynamoRepository
from src.processor.repository.ia_repository import IARepository
from src.processor.services.ia_service import IAService
from src.processor.services.notification_service import NotificationService
from src.processor.services.status_service import StatusService
from src.processor.usecase.combined_processing_usecase import CombinedProcessingUseCase
from src.processor.utils.error_handler import ErrorHandler, ProcessingError

logger = logging.getLogger(__name__)


class ProcessingService:
    def __init__(self):
        self.dynamo_repository = DynamoRepository()
        self.ia_repository = IARepository()
        self.ia_service = IAService(ia_repository=self.ia_repository)
        self.status_service = StatusService(dynamo_repository=self.dynamo_repository)
        self.notification_service = NotificationService()
        self.combined_usecase = CombinedProcessingUseCase(
            ia_service=self.ia_service,
            status_service=self.status_service,
            notification_service=self.notification_service,
            dynamo_repository=self.dynamo_repository,
        )

    async def process_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        request_id = message.get("request_id")

        try:
            self._validate_message(message)

            logger.info(f"Processando mensagem para request_id: {request_id}")

            result = await self.combined_usecase.execute_processing(
                request_id=request_id,
                image_url=message.get("image_url"),
                user_id=message.get("user_id"),
                result_upload_url=message.get("result_upload_url"),
                metadata=message.get("metadata", {}),
                maturation_threshold=message.get("maturation_threshold", 0.6),
            )

            logger.info(f"Processamento concluído com sucesso para request_id: {request_id}")
            return {
                "status": "success",
                "request_id": request_id,
                "result": {
                    "status": result.status,
                    "request_id": result.request_id,
                    "processing_time_ms": result.processing_time_ms,
                    "image_result_url": result.image_result_url,
                },
            }

        except ProcessingError as e:
            logger.error(f"Erro de processamento para request_id {request_id}: {e}")
            return ErrorHandler.create_error_response(e, request_id=request_id, context="message_processing")

        except Exception as e:
            logger.exception(f"Erro inesperado no processamento da mensagem: {e}")
            processing_error = ProcessingError(message=f"Erro inesperado: {str(e)}", original_error=e)
            return ErrorHandler.create_error_response(
                processing_error, request_id=request_id, context="message_processing"
            )

    def _validate_message(self, message: Dict[str, Any]) -> None:
        required_fields = ["request_id", "image_url", "user_id"]
        missing_fields = [field for field in required_fields if not message.get(field)]

        if missing_fields:
            raise ProcessingError(
                message=f"Campos obrigatórios ausentes: {', '.join(missing_fields)}",
                error_code=ErrorHandler.categorize_error(ValueError("validation error")),
            )

        if not isinstance(message.get("metadata"), dict):
            raise ProcessingError(
                message="Campo 'metadata' deve ser um dicionário",
                error_code=ErrorHandler.categorize_error(ValueError("validation error")),
            )

        maturation_threshold = message.get("maturation_threshold", 0.6)
        if not isinstance(maturation_threshold, (int, float)) or not (0.0 <= maturation_threshold <= 1.0):
            raise ProcessingError(
                message="Campo 'maturation_threshold' deve ser um número entre 0.0 e 1.0",
                error_code=ErrorHandler.categorize_error(ValueError("validation error")),
            )
        self._validate_metadata(message.get("metadata", {}))

    def _validate_metadata(self, metadata: Dict[str, Any]) -> None:
        required_metadata_fields = ["image_id", "location"]
        missing_metadata = [field for field in required_metadata_fields if field not in metadata or not metadata[field]]

        if missing_metadata:
            raise ProcessingError(
                message=f"Campos obrigatórios ausentes em metadata: {', '.join(missing_metadata)}",
                error_code=ErrorHandler.categorize_error(ValueError("validation error")),
            )
