import logging
from enum import Enum
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class ErrorCode(Enum):
    PROCESSING_ERROR = "PROCESSING_ERROR"
    NETWORK_ERROR = "NETWORK_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    IA_SERVICE_ERROR = "IA_SERVICE_ERROR"
    STORAGE_ERROR = "STORAGE_ERROR"
    TIMEOUT_ERROR = "TIMEOUT_ERROR"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"


class ProcessingError(Exception):
    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.UNKNOWN_ERROR,
        details: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.original_error = original_error


class ErrorHandler:
    @staticmethod
    def categorize_error(error: Exception) -> ErrorCode:
        error_str = str(error).lower()

        if "timeout" in error_str or "timed out" in error_str:
            return ErrorCode.TIMEOUT_ERROR
        elif "network" in error_str or "connection" in error_str:
            return ErrorCode.NETWORK_ERROR
        elif "validation" in error_str or "invalid" in error_str:
            return ErrorCode.VALIDATION_ERROR
        elif "s3" in error_str or "dynamodb" in error_str:
            return ErrorCode.STORAGE_ERROR
        elif "ia" in error_str or "model" in error_str:
            return ErrorCode.IA_SERVICE_ERROR
        else:
            return ErrorCode.PROCESSING_ERROR

    @staticmethod
    def create_error_response(
        error: Exception, request_id: Optional[str] = None, context: Optional[str] = None
    ) -> Dict[str, Any]:
        if isinstance(error, ProcessingError):
            error_code = error.error_code
            message = error.message
            details = error.details
        else:
            error_code = ErrorHandler.categorize_error(error)
            message = str(error)
            details = {"original_error": str(error)}

        error_response = {"error_code": error_code.value, "error_message": message, "error_details": details}

        if request_id:
            error_response["request_id"] = request_id

        if context:
            error_response["context"] = context

        logger.error(f"Resposta de erro criada: {error_response}")

        return error_response

    @staticmethod
    def is_retryable_error(error: Exception) -> bool:
        if isinstance(error, ProcessingError):
            non_retryable = [ErrorCode.VALIDATION_ERROR, ErrorCode.UNKNOWN_ERROR]
            return error.error_code not in non_retryable

        error_str = str(error).lower()
        non_retryable_patterns = ["validation", "invalid", "not found", "unauthorized", "forbidden"]

        return not any(pattern in error_str for pattern in non_retryable_patterns)
