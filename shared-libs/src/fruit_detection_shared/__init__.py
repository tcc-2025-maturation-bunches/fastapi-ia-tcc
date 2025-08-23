"""
Fruit Detection Shared Library
Biblioteca compartilhada para o sistema de detecção e maturação de frutas
"""

__version__ = "0.1.0"

from .domain.entities import CombinedResult, Device, Image
from .domain.models import (
    CombinedContractResponse,
    CombinedProcessingRequest,
    ContractDetection,
    ContractDetectionResult,
    ContractDetectionSummary,
    ProcessingMetadata,
)
from .infra.external import DynamoClient, EC2Client, S3Client, SQSClient
from .mappers import ContractResponseMapper, RequestSummaryMapper

__all__ = [
    "CombinedResult",
    "Device",
    "Image",
    "CombinedContractResponse",
    "CombinedProcessingRequest",
    "ContractDetection",
    "ContractDetectionResult",
    "ContractDetectionSummary",
    "ProcessingMetadata",
    "DynamoClient",
    "EC2Client",
    "S3Client",
    "SQSClient",
    "ContractResponseMapper",
    "RequestSummaryMapper",
]
