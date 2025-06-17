from datetime import datetime, timezone
from typing import List, Optional

from pydantic import BaseModel, Field


class ImageMetadata(BaseModel):
    device_info: Optional[str] = None
    timestamp: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))
    location: Optional[str] = None


class MaturationInfo(BaseModel):
    score: float
    category: str
    estimated_days_until_spoilage: Optional[int] = None


class BoundingBox(BaseModel):
    x: float
    y: float
    width: float
    height: float

    @classmethod
    def from_list(cls, coords: List[float]) -> "BoundingBox":
        return cls(x=coords[0], y=coords[1], width=coords[2], height=coords[3])


class DetectionInfo(BaseModel):
    class_name: str
    confidence: float
    bounding_box: List[float]
    maturation_level: Optional[MaturationInfo] = None


class ProcessingSummary(BaseModel):
    total_objects: Optional[int] = None
    detection_time_ms: Optional[int] = None
    average_maturation_score: Optional[float] = None


class ColorAnalysis(BaseModel):
    green_ratio: float
    yellow_ratio: float
    brown_ratio: float


class MaturationInfo(BaseModel):
    score: float
    category: str
    estimated_days_until_spoilage: Optional[int] = None
    color_analysis: Optional[ColorAnalysis] = None


class ModelVersions(BaseModel):
    detection: str = "unknown"
    maturation: str = "unknown"

    def __init__(self, **data):
        if isinstance(data.get("detection"), dict):
            super().__init__(
                detection=data["detection"].get("detection", "unknown"),
                maturation=data["detection"].get("maturation", "unknown"),
            )
        else:
            super().__init__(**data)


class ContractDetectionSummary(BaseModel):
    total_objects: int
    objects_with_maturation: int
    detection_time_ms: int
    maturation_time_ms: int
    average_maturation_score: float
    model_versions: Optional[ModelVersions] = None

    def __init__(self, **data):
        if "model_versions" in data and isinstance(data["model_versions"], dict):
            data["model_versions"] = ModelVersions(**data["model_versions"])
        super().__init__(**data)


class ImageDimensions(BaseModel):
    width: int
    height: int


class MaturationDistribution(BaseModel):
    verde: int = 0
    madura: int = 0
    passada: int = 0
    nao_analisado: int = 0


class ProcessingMetadata(BaseModel):
    image_dimensions: ImageDimensions
    maturation_distribution: MaturationDistribution
