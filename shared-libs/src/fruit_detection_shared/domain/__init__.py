"""
Domain Layer - Fruit Detection Shared
Camada de domínio com entidades, modelos e regras de negócio
"""

from .entities import CombinedResult, Device, Image, User
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
    "User",
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
