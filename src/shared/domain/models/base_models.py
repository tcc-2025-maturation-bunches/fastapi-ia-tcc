from datetime import datetime, timezone
from typing import List, Optional

from pydantic import BaseModel, Field


class ImageMetadata(BaseModel):
    """Metadados da imagem enviada pelo cliente."""

    device_info: Optional[str] = None
    timestamp: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))
    location: Optional[str] = None


class MaturationInfo(BaseModel):
    """Informações sobre o nível de maturação."""

    score: float
    category: str
    estimated_days_until_spoilage: Optional[int] = None


class BoundingBox(BaseModel):
    """Coordenadas da caixa delimitadora."""

    x: float
    y: float
    width: float
    height: float

    @classmethod
    def from_list(cls, coords: List[float]) -> "BoundingBox":
        """Cria uma instância a partir de uma lista [x, y, width, height]."""
        return cls(x=coords[0], y=coords[1], width=coords[2], height=coords[3])


class DetectionInfo(BaseModel):
    """Informação sobre um objeto detectado."""

    class_name: str
    confidence: float
    bounding_box: List[float]
    maturation_level: Optional[MaturationInfo] = None


class ProcessingSummary(BaseModel):
    """Resumo do processamento."""

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
    detection: str
    maturation: str


class ContractDetectionSummary(BaseModel):
    total_objects: int
    objects_with_maturation: int
    detection_time_ms: int
    maturation_time_ms: int
    average_maturation_score: float
    model_versions: ModelVersions


class ImageDimensions(BaseModel):
    width: int
    height: int


class MaturationDistribution(BaseModel):
    unripe: int
    semi_ripe: int = Field(alias="semi-ripe")
    ripe: int
    overripe: int
    not_analyzed: int


class ProcessingMetadata(BaseModel):
    image_dimensions: ImageDimensions
    maturation_distribution: MaturationDistribution
    preprocessing_time_ms: int
