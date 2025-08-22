# src/shared/domain/models/http_models.py
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, HttpUrl

from src.domain.enums.ia_model_type_enum import ModelType
from src.domain.models.base_models import (
    BoundingBox,
    DetectionInfo,
    ImageMetadata,
    MaturationInfo,
    ProcessingSummary,
)
from src.domain.models.combined_models import (
    CombinedContractResponse,
    CombinedProcessingRequest,
    ProcessingConfig,
)
from src.domain.models.device_models import (
    BulkDeviceAction,
    DeviceActivityResponse,
    DeviceAlertRequest,
    DeviceCaptureHistory,
    DeviceConfigUpdate,
    DeviceDashboardResponse,
    DeviceMaintenanceRequest,
    DeviceRegistrationRequest,
    DeviceResponse,
    DeviceSetupResponse,
    DeviceStatsResponse,
    DeviceStatusUpdate,
    GlobalConfigRequest,
    ImageUploadProcessRequest,
    ProcessingJobResponse,
)
from src.domain.models.status_models import HealthCheckResponse, ServiceStatusResponse

__all__ = [
    "ImageMetadata",
    "BoundingBox",
    "MaturationInfo",
    "DetectionInfo",
    "ProcessingSummary",
    "ProcessImageRequest",
    "ProcessingResponse",
    "PresignedUrlRequest",
    "PresignedUrlResponse",
    "ProcessingStatusResponse",
    "CombinedProcessingRequest",
    "CombinedContractResponse",
    "ProcessingConfig",
    "DeviceRegistrationRequest",
    "DeviceResponse",
    "DeviceStatusUpdate",
    "DeviceConfigUpdate",
    "ImageUploadProcessRequest",
    "ProcessingJobResponse",
    "DeviceStatsResponse",
    "DeviceCaptureHistory",
    "GlobalConfigRequest",
    "DeviceSetupResponse",
    "DeviceDashboardResponse",
    "DeviceActivityResponse",
    "DeviceAlertRequest",
    "DeviceMaintenanceRequest",
    "BulkDeviceAction",
    "HealthCheckResponse",
    "ServiceStatusResponse",
]


class ProcessImageRequest(BaseModel):
    image_url: HttpUrl
    user_id: str
    model_type: ModelType
    metadata: Optional[ImageMetadata] = None


class ProcessingResponse(BaseModel):
    request_id: str
    image_id: str
    model_type: str
    status: str
    processing_timestamp: datetime
    results: List[DetectionInfo]
    summary: ProcessingSummary
    image_result_url: Optional[HttpUrl] = None
    error_message: Optional[str] = None


class PresignedUrlRequest(BaseModel):
    filename: str
    content_type: str
    user_id: str


class PresignedUrlResponse(BaseModel):
    upload_url: HttpUrl
    image_id: str
    expires_in_seconds: int


class ProcessingStatusResponse(BaseModel):
    request_id: str
    status: str  # "queued", "processing", "detecting", "detecting_maturation", "completed", "error"
    progress: Optional[float] = Field(None, ge=0.0, le=1.0)
    estimated_completion_time: Optional[datetime] = None
    error_message: Optional[str] = None
