import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile

from src.modules.storage.usecase.get_result_usecase import GetResultUseCase
from src.modules.storage.usecase.image_upload_usecase import ImageUploadUseCase
from src.shared.domain.models.http_models import PresignedUrlRequest, PresignedUrlResponse, ProcessingResponse

logger = logging.getLogger(__name__)
storage_router = APIRouter(prefix="/storage", tags=["Storage"])


def get_image_upload_usecase():
    return ImageUploadUseCase()


def get_result_usecase():
    return GetResultUseCase()


@storage_router.post("/presigned-url", response_model=PresignedUrlResponse)
async def generate_presigned_url(
    request: PresignedUrlRequest,
    image_upload_usecase: ImageUploadUseCase = Depends(get_image_upload_usecase),
):
    """Gera uma URL pré-assinada para upload direto para o S3."""
    try:
        presigned_url_data = await image_upload_usecase.generate_presigned_url(
            filename=request.filename,
            content_type=request.content_type,
            user_id=request.user_id,
        )

        return PresignedUrlResponse(
            upload_url=presigned_url_data["upload_url"],
            image_id=presigned_url_data["image_id"],
            expires_in_seconds=presigned_url_data["expires_in_seconds"],
        )

    except Exception as e:
        logger.exception(f"Erro ao gerar URL pré-assinada: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao gerar URL pré-assinada: {str(e)}")

@storage_router.post("/presigned-result-url", response_model=PresignedUrlResponse)
async def generate_presigned_result_url(
    request: PresignedUrlRequest,
    image_upload_usecase: ImageUploadUseCase = Depends(get_image_upload_usecase),
):
    """Gera uma URL pré-assinada para upload de resultados de processamento."""
    try:
        presigned_url_data = await image_upload_usecase.generate_result_presigned_url(
            filename=request.filename,
            content_type=request.content_type,
            user_id=request.user_id,
        )

        return PresignedUrlResponse(
            upload_url=presigned_url_data["upload_url"],
            image_id=presigned_url_data["result_id"],
            expires_in_seconds=presigned_url_data["expires_in_seconds"],
        )

    except Exception as e:
        logger.exception(f"Erro ao gerar URL pré-assinada para resultado: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao gerar URL pré-assinada para resultado: {str(e)}")

@storage_router.post("/upload", response_model=dict)
async def upload_image(
    file: UploadFile = File(...),
    user_id: str = Form(...),
    metadata: Optional[str] = Form(None),
    image_upload_usecase: ImageUploadUseCase = Depends(get_image_upload_usecase),
):
    """Faz upload de uma imagem para o S3."""
    try:
        metadata_dict = None
        if metadata:
            import json

            try:
                metadata_dict = json.loads(metadata)
            except json.JSONDecodeError:
                raise HTTPException(
                    status_code=400,
                    detail="Formato de metadata inválido. Deve ser JSON válido.",
                )

        image = await image_upload_usecase.upload_image(
            file_obj=file.file,
            filename=file.filename,
            user_id=user_id,
            content_type=file.content_type,
            metadata=metadata_dict,
        )

        return {
            "image_id": image.image_id,
            "image_url": image.image_url,
            "message": "Imagem enviada com sucesso",
        }

    except Exception as e:
        logger.exception(f"Erro ao fazer upload de imagem: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao fazer upload de imagem: {str(e)}")


@storage_router.get("/results/request/{request_id}", response_model=ProcessingResponse)
async def get_result_by_request_id(request_id: str, result_usecase: GetResultUseCase = Depends(get_result_usecase)):
    """Recupera um resultado de processamento pelo ID da requisição."""
    try:
        result = await result_usecase.get_by_request_id(request_id)

        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"Resultado não encontrado para request_id: {request_id}",
            )

        return ProcessingResponse(**result.to_dict())

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Erro ao recuperar resultado por request_id: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao recuperar resultado: {str(e)}")


@storage_router.get("/results/image/{image_id}", response_model=List[ProcessingResponse])
async def get_results_by_image_id(image_id: str, result_usecase: GetResultUseCase = Depends(get_result_usecase)):
    """Recupera todos os resultados de processamento para uma imagem."""
    try:
        results = await result_usecase.get_by_image_id(image_id)

        if not results:
            raise HTTPException(
                status_code=404,
                detail=f"Nenhum resultado encontrado para image_id: {image_id}",
            )

        return [ProcessingResponse(**result.to_dict()) for result in results]

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Erro ao recuperar resultados por image_id: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao recuperar resultados: {str(e)}")


@storage_router.get("/results/user/{user_id}", response_model=List[ProcessingResponse])
async def get_results_by_user_id(
    user_id: str,
    limit: int = Query(10, ge=1, le=100),
    result_usecase: GetResultUseCase = Depends(get_result_usecase),
):
    """Recupera os resultados de processamento para um usuário."""
    try:
        results = await result_usecase.get_by_user_id(user_id, limit)

        if not results:
            raise HTTPException(
                status_code=404,
                detail=f"Nenhum resultado encontrado para user_id: {user_id}",
            )

        return [ProcessingResponse(**result.to_dict()) for result in results]

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Erro ao recuperar resultados por user_id: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao recuperar resultados: {str(e)}")
