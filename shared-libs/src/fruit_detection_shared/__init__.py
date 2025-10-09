"""
Fruit Detection Shared Library
Biblioteca compartilhada para o sistema de detecção e maturação de frutas
"""

__version__ = "0.2.0"

from .domain.entities import CombinedResult, Device, Image, User
from .domain.models import (
    CombinedContractResponse,
    ContractDetection,
    ContractDetectionResult,
    ContractDetectionSummary,
    ProcessingMetadata,
)
from .domain.models.request_models import (
    BatchProcessingRequest,
    BatchProcessingResponse,
    CombinedProcessingRequest,
    ProcessingResponse,
    ProcessingStatusResponse,
    QueueStatsResponse,
    validate_image_metadata_shared,
)
from .domain.models.request_models import (
    ProcessingMetadata as SharedProcessingMetadata,
)
from .infra.external import DynamoClient, EC2Client, S3Client, SNSClient, SQSClient
from .mappers import ContractResponseMapper, RequestSummaryMapper

__all__ = [
    # Entities
    "CombinedResult",
    "Device",
    "Image",
    "User",
    # Contract Models (usados internamente entre serviços)
    "CombinedContractResponse",
    "ContractDetection",
    "ContractDetectionResult",
    "ContractDetectionSummary",
    "ProcessingMetadata",
    # Request/Response Models (usados por APIs públicas)
    "SharedProcessingMetadata",
    "CombinedProcessingRequest",
    "ProcessingResponse",
    "ProcessingStatusResponse",
    "BatchProcessingRequest",
    "BatchProcessingResponse",
    "QueueStatsResponse",
    "validate_image_metadata_shared",
    # Infrastructure Clients
    "DynamoClient",
    "EC2Client",
    "S3Client",
    "SQSClient",
    "SNSClient",
    # Mappers
    "ContractResponseMapper",
    "RequestSummaryMapper",
]
