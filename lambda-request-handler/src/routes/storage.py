import logging
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, field_validator

from src.app.config import settings
from src.services.presigned_service import PresignedURLService
from src.utils.validators import validate_user_id

logger = logging.getLogger(__name__)

storage_router = APIRouter()


class PresignedURLRequest(BaseModel):
    filename: str = Field(..., min_length=1, max_length=255)
    content_type: str = Field(..., min_length=1)
    user_id: str = Field(..., min_length=1, max_length=128)

    @field_validator("user_id")
    @classmethod
    def validate_user_id_field(cls, v):
        return validate_user_id(v)

    @field_validator("content_type")
    @classmethod
    def validate_content_type(cls, v):
        if v not in settings.ALLOWED_IMAGE_TYPES:
            raise ValueError(f"Tipo de conteúdo inválido. Tipos permitidos: {', '.join(settings.ALLOWED_IMAGE_TYPES)}")
        return v


class PresignedURLResponse(BaseModel):
    upload_url: str
    public_url: str
    image_id: str
    key: str
    expires_in_seconds: int
    expires_at: str


class BatchPresignedURLRequest(BaseModel):
    requests: List[PresignedURLRequest] = Field(..., min_items=1, max_items=10)


@storage_router.post(
    "/presigned-url",
    response_model=PresignedURLResponse,
    status_code=status.HTTP_200_OK,
    summary="Gerar URL pré-assinada para upload de imagem",
)
async def generate_presigned_url(request: PresignedURLRequest):
    try:
        logger.info(f"Gerando URL pré-assinada para usuário {request.user_id}, arquivo: {request.filename}")

        presigned_service = PresignedURLService()
        url_data = await presigned_service.generate_upload_url(
            filename=request.filename, content_type=request.content_type, user_id=request.user_id, purpose="image"
        )

        return PresignedURLResponse(
            upload_url=url_data["upload_url"],
            public_url=url_data["public_url"],
            image_id=url_data["image_id"],
            key=url_data["key"],
            expires_in_seconds=url_data["expires_in_seconds"],
            expires_at=url_data["expires_at"],
        )

    except ValueError as e:
        logger.warning(f"Requisição inválida: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.exception(f"Erro ao gerar URL pré-assinada: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Falha ao gerar URL pré-assinada")


@storage_router.post(
    "/presigned-result-url",
    response_model=PresignedURLResponse,
    status_code=status.HTTP_200_OK,
    summary="Gerar URL pré-assinada para upload de resultado",
)
async def generate_presigned_result_url(request: PresignedURLRequest):
    try:
        logger.info(f"Gerando URL pré-assinada de resultado para usuário {request.user_id}")

        presigned_service = PresignedURLService()
        url_data = await presigned_service.generate_upload_url(
            filename=request.filename, content_type=request.content_type, user_id=request.user_id, purpose="result"
        )

        url_data["result_id"] = url_data.pop("result_id", url_data.get("image_id"))

        return PresignedURLResponse(
            upload_url=url_data["upload_url"],
            public_url=url_data["public_url"],
            image_id=url_data["result_id"],
            key=url_data["key"],
            expires_in_seconds=url_data["expires_in_seconds"],
            expires_at=url_data["expires_at"],
        )

    except ValueError as e:
        logger.warning(f"Requisição inválida: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.exception(f"Erro ao gerar URL pré-assinada de resultado: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Falha ao gerar URL pré-assinada de resultado"
        )


@storage_router.post(
    "/batch-presigned-urls",
    response_model=List[Dict[str, Any]],
    status_code=status.HTTP_200_OK,
    summary="Gerar múltiplas URLs pré-assinadas",
)
async def generate_batch_presigned_urls(request: BatchPresignedURLRequest):
    try:
        logger.info(f"Gerando URLs pré-assinadas em lote: {len(request.requests)} URLs")

        presigned_service = PresignedURLService()
        requests_data = [
            {"filename": req.filename, "content_type": req.content_type, "user_id": req.user_id, "purpose": "image"}
            for req in request.requests
        ]

        results = await presigned_service.generate_batch_urls(requests_data)

        return results

    except Exception as e:
        logger.exception(f"Erro ao gerar URLs pré-assinadas em lote: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Falha ao gerar URLs pré-assinadas em lote"
        )


@storage_router.get(
    "/validate/{key:path}",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Validar se arquivo existe no S3",
)
async def validate_file_exists(key: str, bucket: str = "images"):
    try:
        presigned_service = PresignedURLService()

        if bucket == "results":
            bucket_name = settings.S3_RESULTS_BUCKET
        else:
            bucket_name = settings.S3_IMAGES_BUCKET

        exists = await presigned_service.validate_file_exists(key, bucket_name)

        return {"exists": exists, "key": key, "bucket": bucket_name}

    except Exception as e:
        logger.exception(f"Erro ao validar existência do arquivo: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Falha ao validar existência do arquivo"
        )
