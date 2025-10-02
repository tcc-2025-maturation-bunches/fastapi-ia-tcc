import logging
import re
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, HttpUrl, field_validator, model_validator

logger = logging.getLogger(__name__)


class ProcessingMetadata(BaseModel):
    """
    Metadados para processamento de imagens - usado por Request Handler e Processing AI
    """

    user_id: str = Field(..., min_length=1, max_length=128)
    image_id: str = Field(..., min_length=1, max_length=128)
    location: str = Field(..., min_length=1, max_length=255)
    processing_type: Optional[str] = "combined"
    device_id: Optional[str] = Field(None, min_length=1, max_length=100)
    notes: Optional[str] = None
    capture_timestamp: Optional[str] = None

    class Config:
        extra = "allow"
        json_schema_extra = {
            "example": {
                "user_id": "user123",
                "image_id": "img-456",
                "location": "dock-1",
                "processing_type": "combined",
                "device_id": "rpi-dock-001",
                "notes": "Teste de captura automática",
                "capture_timestamp": "2025-01-01T12:00:00Z",
            }
        }

    @field_validator("user_id")
    @classmethod
    def validate_user_id_field(cls, v):
        if not isinstance(v, str) or len(v.strip()) == 0:
            raise ValueError("user_id deve ser uma string não vazia")

        if not re.match(r"^[a-zA-Z0-9_-]+$", v):
            raise ValueError("user_id deve conter apenas caracteres alfanuméricos, hífens e underscores")

        return v.strip()

    @field_validator("device_id")
    @classmethod
    def validate_device_id_field(cls, v):
        if v is not None:
            if not isinstance(v, str) or len(v.strip()) == 0:
                raise ValueError("device_id deve ser uma string não vazia")

            if not re.match(r"^[a-zA-Z0-9_-]+$", v):
                raise ValueError("device_id deve conter apenas caracteres alfanuméricos, hífens e underscores")

            return v.strip()
        return v

    @field_validator("image_id")
    @classmethod
    def validate_image_id_field(cls, v):
        if not isinstance(v, str) or len(v.strip()) == 0:
            raise ValueError("image_id deve ser uma string não vazia")
        return v.strip()

    @field_validator("location")
    @classmethod
    def validate_location_field(cls, v):
        if not isinstance(v, str) or len(v.strip()) == 0:
            raise ValueError("location deve ser uma string não vazia")
        return v.strip()


class CombinedProcessingRequest(BaseModel):
    """
    Requisição para processamento combinado (detecção + maturação)
    Usado por Request Handler e consumido por Processing AI
    """

    image_url: HttpUrl
    result_upload_url: Optional[HttpUrl] = None
    metadata: ProcessingMetadata
    maturation_threshold: float = Field(0.6, ge=0.0, le=1.0)

    class Config:
        json_schema_extra = {
            "example": {
                "image_url": "https://bucket.s3.amazonaws.com/user123/image.jpg",
                "result_upload_url": "https://bucket.s3.amazonaws.com/results/result.jpg",
                "metadata": {
                    "user_id": "user123",
                    "image_id": "img-456",
                    "location": "dock-1",
                    "device_id": "rpi-dock-001",
                },
                "maturation_threshold": 0.6,
            }
        }

    @field_validator("image_url")
    @classmethod
    def validate_image_url(cls, v):
        url_str = str(v)
        # Validação básica - pode ser customizada por cada Lambda
        if not url_str.startswith("https://"):
            raise ValueError("image_url deve usar HTTPS")
        return v

    @model_validator(mode="after")
    def validate_consistency(self):
        # Validações cruzadas entre campos
        if self.metadata.processing_type and self.metadata.processing_type not in [
            "combined",
            "detection",
            "maturation",
        ]:
            raise ValueError("processing_type deve ser 'combined', 'detection' ou 'maturation'")

        return self


class ProcessingResponse(BaseModel):
    """
    Resposta padrão para requisições de processamento
    Usado por Request Handler para responder ao cliente
    """

    request_id: str
    status: str
    message: str
    queue_position: Optional[int] = None
    estimated_wait_time_seconds: Optional[int] = None
    submitted_at: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "request_id": "req-abc123",
                "status": "queued",
                "message": "Solicitação enfileirada com sucesso",
                "queue_position": 3,
                "estimated_wait_time_seconds": 90,
            }
        }

    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        valid_statuses = ["queued", "processing", "completed", "error", "failed"]
        if v not in valid_statuses:
            raise ValueError(f"Status deve ser um de: {', '.join(valid_statuses)}")
        return v


class ProcessingStatusResponse(BaseModel):
    """
    Resposta detalhada de status de processamento
    Usado por Request Handler e Results Query
    """

    request_id: str
    status: str
    progress: float = Field(ge=0.0, le=1.0)
    created_at: str
    updated_at: str
    elapsed_seconds: float
    is_timeout: bool
    metadata: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    error_code: Optional[str] = None
    processing_stages: Optional[Dict[str, Any]] = None

    class Config:
        json_schema_extra = {
            "example": {
                "request_id": "req-abc123",
                "status": "processing",
                "progress": 0.7,
                "created_at": "2025-01-01T12:00:00Z",
                "updated_at": "2025-01-01T12:02:30Z",
                "elapsed_seconds": 150,
                "is_timeout": False,
                "metadata": {"device_id": "rpi-dock-001", "user_id": "user123"},
            }
        }


class BatchProcessingRequest(BaseModel):
    """
    Requisição para processamento em lote
    """

    requests: list[CombinedProcessingRequest] = Field(..., min_length=1, max_length=10)
    batch_id: Optional[str] = None
    priority: Optional[str] = "normal"

    class Config:
        json_schema_extra = {
            "example": {
                "requests": [
                    {
                        "image_url": "https://bucket.s3.amazonaws.com/img1.jpg",
                        "metadata": {"user_id": "user123", "image_id": "img-1", "location": "dock-1"},
                    }
                ],
                "batch_id": "batch-abc123",
                "priority": "normal",
            }
        }

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v):
        if v and v not in ["low", "normal", "high", "urgent"]:
            raise ValueError("Priority deve ser 'low', 'normal', 'high' ou 'urgent'")
        return v


class BatchProcessingResponse(BaseModel):
    """
    Resposta para processamento em lote
    """

    batch_id: str
    total_requests: int
    successful_requests: int
    failed_requests: int
    requests: list[ProcessingResponse]
    estimated_completion_time: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "batch_id": "batch-abc123",
                "total_requests": 5,
                "successful_requests": 4,
                "failed_requests": 1,
                "requests": [],
                "estimated_completion_time": "2025-01-01T12:10:00Z",
            }
        }


class QueueStatsResponse(BaseModel):
    """
    Estatísticas da fila de processamento
    """

    queue_depth: int
    processing_count: int
    total_pending: int
    estimated_wait_time_seconds: int
    estimated_wait_time_minutes: float
    queue_url: Optional[str] = None
    timestamp: str

    class Config:
        json_schema_extra = {
            "example": {
                "queue_depth": 15,
                "processing_count": 3,
                "total_pending": 18,
                "estimated_wait_time_seconds": 540,
                "estimated_wait_time_minutes": 9.0,
                "timestamp": "2025-01-01T12:00:00Z",
            }
        }


# Validators compartilhados
def validate_image_metadata_shared(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validação compartilhada de metadados de imagem
    Pode ser usada por qualquer Lambda que processe metadados
    """
    required_fields = ["user_id", "image_id", "location"]

    for field in required_fields:
        if field not in metadata:
            raise ValueError(f"Campo obrigatório ausente: {field}")

        if not isinstance(metadata[field], str) or len(metadata[field].strip()) == 0:
            raise ValueError(f"Campo {field} deve ser uma string não vazia")

    # Validações específicas
    if len(metadata["user_id"]) > 128:
        raise ValueError("user_id não pode ter mais de 128 caracteres")

    if len(metadata["image_id"]) > 128:
        raise ValueError("image_id não pode ter mais de 128 caracteres")

    if len(metadata["location"]) > 255:
        raise ValueError("location não pode ter mais de 255 caracteres")

    # Validar device_id se presente
    if "device_id" in metadata and metadata["device_id"]:
        device_id = metadata["device_id"]
        if not isinstance(device_id, str) or len(device_id) > 100:
            raise ValueError("device_id deve ser uma string com até 100 caracteres")

        if not re.match(r"^[a-zA-Z0-9_-]+$", device_id):
            raise ValueError("device_id deve conter apenas caracteres alfanuméricos, hífens e underscores")

    # Validar notes se presente
    if "notes" in metadata and metadata["notes"]:
        if len(str(metadata["notes"])) > 1000:
            raise ValueError("notes não pode ter mais de 1000 caracteres")

    return metadata
