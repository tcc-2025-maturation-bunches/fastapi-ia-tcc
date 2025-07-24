import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field, HttpUrl, field_validator, model_validator
from services.presigned_service import PresignedURLService
from services.queue_service import QueueService
from services.status_service import ProcessingStatus, StatusService
from utils.validators import validate_image_metadata, validate_request_id, validate_user_id

from app.config import settings

logger = logging.getLogger(__name__)

combined_router = APIRouter()


class ProcessingMetadata(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=128)
    image_id: str = Field(..., min_length=1, max_length=128)
    location: str = Field(..., min_length=1, max_length=255)
    processing_type: Optional[str] = "combined"
    notes: Optional[str] = None
    device_id: Optional[str] = None
    capture_timestamp: Optional[str] = None

    class Config:
        extra = "allow"


class CombinedProcessingRequest(BaseModel):
    image_url: HttpUrl
    result_upload_url: Optional[HttpUrl] = None
    metadata: ProcessingMetadata
    maturation_threshold: float = Field(0.6, ge=0.0, le=1.0)

    @field_validator("user_id")
    @classmethod
    def validate_user_id_field(cls, v):
        return validate_user_id(v)

    @model_validator(mode="after")
    def validate_full_metadata(self):
        validate_image_metadata(self.model_dump())
        return self

    @field_validator("image_url")
    @classmethod
    def validate_image_url(cls, v):
        url_str = str(v)
        if not any(bucket in url_str for bucket in [settings.S3_IMAGES_BUCKET, "s3.amazonaws.com"]):
            logger.warning(f"URL da imagem não é do bucket S3 esperado: {url_str}")
        return v


class ProcessingResponse(BaseModel):
    request_id: str
    status: str
    message: str
    queue_position: Optional[int] = None
    estimated_wait_time_seconds: Optional[int] = None


class StatusResponse(BaseModel):
    request_id: str
    status: str
    progress: float
    created_at: str
    updated_at: str
    elapsed_seconds: float
    is_timeout: bool
    metadata: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    error_code: Optional[str] = None


@combined_router.post(
    "/process",
    response_model=ProcessingResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Enviar imagem para processamento combinado",
)
async def process_combined(request: CombinedProcessingRequest):
    try:
        validate_image_metadata(request.metadata.model_dump())
        request_id = f"req-{uuid.uuid4().hex[:12]}"
        validate_request_id(request_id)
        logger.info(f"Solicitação de processamento {request_id} para usuário {request.metadata.user_id}")

        queue_service = QueueService()
        status_service = StatusService()

        result_upload_url = request.result_upload_url
        if not result_upload_url:
            presigned_service = PresignedURLService()
            url_data = await presigned_service.generate_upload_url(
                filename=f"{request.metadata.image_id}_result.jpg",
                content_type="image/jpeg",
                user_id=request.metadata.user_id,
                purpose="result",
            )
            result_upload_url = url_data["upload_url"]

        await status_service.create_initial_status(
            request_id=request_id,
            user_id=request.metadata.user_id,
            image_url=str(request.image_url),
            metadata=request.metadata.model_dump(),
        )

        await queue_service.send_processing_message(
            image_url=str(request.image_url),
            user_id=request.metadata.user_id,
            request_id=request_id,
            metadata=request.metadata.model_dump(),
            result_upload_url=str(result_upload_url),
            maturation_threshold=request.maturation_threshold,
        )

        queue_attrs = await queue_service.get_queue_attributes()
        queue_depth = queue_attrs.get("messages_available", 0)

        estimated_wait = queue_depth * 30

        return ProcessingResponse(
            request_id=request_id,
            status="queued",
            message="Solicitação de processamento enfileirada com sucesso",
            queue_position=queue_depth + 1,
            estimated_wait_time_seconds=estimated_wait,
        )

    except ValueError as e:
        logger.warning(f"Solicitação inválida: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.exception(f"Erro ao processar solicitação: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Falha ao enfileirar solicitação de processamento"
        )


@combined_router.get(
    "/status/{request_id}",
    response_model=StatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Obter status de processamento",
)
async def get_processing_status(request_id: str):
    try:
        validate_request_id(request_id)
        status_service = StatusService()
        status_data = await status_service.get_status(request_id)

        if not status_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Solicitação de processamento {request_id} não encontrada",
            )

        return StatusResponse(
            request_id=request_id,
            status=status_data.get("status", "unknown"),
            progress=status_data.get("progress", 0.0),
            created_at=status_data.get("created_at"),
            updated_at=status_data.get("updated_at"),
            elapsed_seconds=status_data.get("elapsed_seconds", 0),
            is_timeout=status_data.get("is_timeout", False),
            metadata=status_data.get("metadata"),
            error_message=status_data.get("error_message"),
            error_code=status_data.get("error_code"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Erro ao obter status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Falha ao recuperar status de processamento"
        )


@combined_router.get(
    "/user/{user_id}/requests",
    response_model=List[StatusResponse],
    status_code=status.HTTP_200_OK,
    summary="Obter solicitações de processamento do usuário",
)
async def get_user_requests(
    user_id: str,
    limit: int = Query(10, ge=1, le=100),
    status_filter: Optional[str] = Query(None, description="Filtrar por status"),
):
    try:
        validate_user_id(user_id)
        status_service = StatusService()

        status_enum = None
        if status_filter:
            try:
                status_enum = ProcessingStatus(status_filter)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail=f"Filtro de status inválido: {status_filter}"
                )

        requests = await status_service.get_user_requests(user_id=user_id, limit=limit, status_filter=status_enum)

        responses = []
        for req in requests:
            responses.append(
                StatusResponse(
                    request_id=req.get("request_id"),
                    status=req.get("status", "unknown"),
                    progress=req.get("progress", 0.0),
                    created_at=req.get("created_at"),
                    updated_at=req.get("updated_at"),
                    elapsed_seconds=0,
                    is_timeout=False,
                    metadata=req.get("metadata"),
                    error_message=req.get("error_message"),
                    error_code=req.get("error_code"),
                )
            )

        return responses

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Erro ao obter solicitações do usuário: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Falha ao recuperar solicitações do usuário"
        )


@combined_router.post(
    "/batch-process",
    response_model=List[ProcessingResponse],
    status_code=status.HTTP_202_ACCEPTED,
    summary="Enviar múltiplas imagens para processamento",
)
async def batch_process(requests: List[CombinedProcessingRequest]):
    try:
        if len(requests) > 10:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Máximo de 10 imagens por solicitação em lote"
            )

        logger.info(f"Solicitação de processamento em lote para {len(requests)} imagens")

        queue_service = QueueService()
        status_service = StatusService()
        presigned_service = PresignedURLService()

        responses = []
        messages = []

        for request in requests:
            request_id = f"req-{uuid.uuid4().hex[:12]}"

            result_upload_url = request.result_upload_url
            if not result_upload_url:
                url_data = await presigned_service.generate_upload_url(
                    filename=f"{request.metadata.image_id}_result.jpg",
                    content_type="image/jpeg",
                    user_id=request.metadata.user_id,
                    purpose="result",
                )
                result_upload_url = url_data["upload_url"]

            await status_service.create_initial_status(
                request_id=request_id,
                user_id=request.metadata.user_id,
                image_url=str(request.image_url),
                metadata=request.metadata.model_dump(),
            )

            messages.append(
                {
                    "request_id": request_id,
                    "image_url": str(request.image_url),
                    "user_id": request.metadata.user_id,
                    "result_upload_url": str(result_upload_url),
                    "maturation_threshold": request.maturation_threshold,
                    "metadata": request.metadata.model_dump(),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "source": "request-handler-lambda",
                }
            )

            responses.append(
                ProcessingResponse(
                    request_id=request_id,
                    status="queued",
                    message="Solicitação de processamento enfileirada",
                    queue_position=None,
                    estimated_wait_time_seconds=None,
                )
            )

        batch_result = await queue_service.send_batch_messages(messages)

        failed_ids = {f["Id"] for f in batch_result.get("failed", [])}
        for idx, response in enumerate(responses):
            if str(idx) in failed_ids:
                response.status = "failed"
                response.message = "Falha ao enfileirar solicitação"

        return responses

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Erro no processamento em lote: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Falha ao processar solicitação em lote"
        )


@combined_router.get(
    "/queue/stats",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Obter estatísticas da fila de processamento",
)
async def get_queue_stats():
    try:
        queue_service = QueueService()
        queue_attrs = await queue_service.get_queue_attributes()

        messages_available = queue_attrs.get("messages_available", 0)
        messages_in_flight = queue_attrs.get("messages_in_flight", 0)
        total_messages = messages_available + messages_in_flight

        avg_processing_time_seconds = 30
        estimated_total_time = total_messages * avg_processing_time_seconds

        return {
            "queue_depth": messages_available,
            "processing_count": messages_in_flight,
            "total_pending": total_messages,
            "estimated_wait_time_seconds": estimated_total_time,
            "estimated_wait_time_minutes": round(estimated_total_time / 60, 1),
            "queue_url": settings.SQS_QUEUE_URL,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as e:
        logger.exception(f"Erro ao obter estatísticas da fila: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Falha ao recuperar estatísticas da fila"
        )
