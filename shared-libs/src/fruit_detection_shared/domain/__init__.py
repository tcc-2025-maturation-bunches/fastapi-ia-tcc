"""
Domain Layer - Fruit Detection Shared
Camada de domínio com entidades, modelos e regras de negócio
"""

from .entities import CombinedResult, Device, Image
from .enums import ModelType
from .exceptions import PartialProcessingError, ProcessingException
from .models import (
    BoundingBox,
    CombinedContractResponse,
    CombinedProcessingRequest,
    ContractDetection,
    ContractDetectionResult,
    ContractDetectionSummary,
    ImageDimensions,
    MaturationDistribution,
    MaturationInfo,
    ProcessingMetadata,
)

__all__ = [
    "CombinedResult",
    "Device",
    "Image",
    "ModelType",
    "ProcessingException",
    "PartialProcessingError",
    "BoundingBox",
    "CombinedContractResponse",
    "CombinedProcessingRequest",
    "ContractDetection",
    "ContractDetectionResult",
    "ContractDetectionSummary",
    "ImageDimensions",
    "MaturationDistribution",
    "MaturationInfo",
    "ProcessingMetadata",
]