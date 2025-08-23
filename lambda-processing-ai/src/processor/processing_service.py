import asyncio
import logging
from typing import Any, Dict

from src.processor.repository.dynamo_repository import DynamoRepository
from src.processor.repository.ia_repository import IARepository
from src.processor.usecase.combined_processing_usecase import CombinedProcessingUseCase
from src.processor.utils.error_handler import ErrorHandler, ProcessingError
from src.processor.utils.retry_handler import retry_on_failure

logger = logging.getLogger(__name__)


class ProcessingService:
    def __init__(self):
        self.dynamo_repository = DynamoRepository()
        self.ia_repository = IARepository()
        self.combined_usecase = CombinedProcessingUseCase(
            ia_repository=self.ia_repository, dynamo_repository=self.dynamo_repository
        )

    @retry_on_failure(max_attempts=3, delay_seconds=5)
    def process_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        try:
            request_id = message.get("request_id")
            image_url = message.get("image_url")
            user_id = message.get("user_id")
            result_upload_url = message.get("result_upload_url")
            metadata = message.get("metadata", {})
            maturation_threshold = message.get("maturation_threshold", 0.6)

            self._validate_message(message)

            logger.info(f"Processando mensagem para request_id: {request_id}")

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                result = loop.run_until_complete(
                    self.combined_usecase.execute_processing(
                        request_id=request_id,
                        image_url=image_url,
                        user_id=user_id,
                        result_upload_url=result_upload_url,
                        metadata=metadata,
                        maturation_threshold=maturation_threshold,
                    )
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

            finally:
                loop.close()

        except ProcessingError as e:
            logger.error(f"Erro de processamento para request_id {message.get('request_id')}: {e}")
            return ErrorHandler.create_error_response(
                e, request_id=message.get("request_id"), context="message_processing"
            )

        except Exception as e:
            logger.exception(f"Erro inesperado no processamento da mensagem: {e}")
            processing_error = ProcessingError(message=f"Erro inesperado: {str(e)}", original_error=e)
            return ErrorHandler.create_error_response(
                processing_error, request_id=message.get("request_id"), context="message_processing"
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
