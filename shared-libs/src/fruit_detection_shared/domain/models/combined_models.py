from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, HttpUrl

from src.shared.domain.models.base_models import ContractDetectionSummary, MaturationInfo, ProcessingMetadata


class CombinedProcessingRequest(BaseModel):
    image_url: HttpUrl
    result_upload_url: Optional[HttpUrl] = None
    metadata: Dict[str, Any]


class ProcessingConfig(BaseModel):
    min_detection_confidence: float = Field(0.6, ge=0.0, le=1.0)
    min_maturation_confidence: float = Field(0.7, ge=0.0, le=1.0)
    enable_auto_maturation: bool = True
    max_results: int = Field(50, ge=1)
    allowed_classes: Optional[List[str]] = None


class ContractDetectionResult(BaseModel):
    class_name: str
    confidence: float
    bounding_box: List[float]
    maturation_level: Optional[MaturationInfo] = None


class ContractDetection(BaseModel):
    results: List[ContractDetectionResult]
    summary: ContractDetectionSummary


class CombinedContractResponse(BaseModel):
    status: str
    request_id: str
    detection: ContractDetection
    image_result_url: Optional[str] = None
    processing_time_ms: int
    processing_metadata: ProcessingMetadata
