"""
Domain Exceptions - Fruit Detection Shared
Exceções específicas do domínio
"""

from .processing_exceptions import PartialProcessingError, ProcessingException

__all__ = [
    "ProcessingException",
    "PartialProcessingError",
]
