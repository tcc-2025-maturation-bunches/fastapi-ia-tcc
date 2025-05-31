import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from src.app.config import settings
from src.modules.ia_integration.usecase.combined_processing_usecase import CombinedProcessingUseCase
from src.shared.domain.models.combined_models import CombinedProcessingRequest, CombinedProcessingResponse
from src.shared.domain.models.http_models import ProcessingStatusResponse

logger = logging.getLogger(__name__)

combined_router = APIRouter(prefix="/combined", tags=["Combined Processing"])


def get_combined_processing_usecase():
    return CombinedProcessingUseCase()


@combined_router.post("/process", response_model=ProcessingStatusResponse)
async def process_image_combined(
    request: CombinedProcessingRequest,
    background_tasks: BackgroundTasks,
    combined_usecase: CombinedProcessingUseCase = Depends(get_combined_processing_usecase),
):
    try:
        metadata = None
        if request.metadata:
            try:
                metadata = request.metadata.model_dump()
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Erro ao processar metadados: {str(e)}")

        maturation_threshold = request.maturation_threshold or settings.MIN_DETECTION_CONFIDENCE

        request_id = await combined_usecase.start_processing(
            image_url=str(request.image_url),
            user_id=request.user_id,
            metadata=metadata,
            maturation_threshold=maturation_threshold,
            location=request.location,
        )

        background_tasks.add_task(
            combined_usecase.execute_in_background,
            request_id=request_id,
            image_url=str(request.image_url),
            user_id=request.user_id,
            metadata=metadata,
            maturation_threshold=maturation_threshold,
            location=request.location,
        )

        return ProcessingStatusResponse(
            request_id=request_id,
            status="processing",
            progress=0.0,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Erro ao iniciar processamento combinado: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao iniciar processamento combinado: {str(e)}")


@combined_router.get("/status/{request_id}", response_model=ProcessingStatusResponse)
async def get_processing_status(
    request_id: str,
    combined_usecase: CombinedProcessingUseCase = Depends(get_combined_processing_usecase),
):
    try:
        status = await combined_usecase.get_processing_status(request_id)

        if not status:
            raise HTTPException(status_code=404, detail=f"Processamento {request_id} não encontrado")

        return status

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Erro ao verificar status do processamento: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao verificar status do processamento: {str(e)}")


@combined_router.get("/results/{image_id}", response_model=Optional[CombinedProcessingResponse])
async def get_combined_results(
    image_id: str,
    combined_usecase: CombinedProcessingUseCase = Depends(get_combined_processing_usecase),
):
    try:
        result = await combined_usecase.get_combined_result(image_id)

        if not result:
            return None

        combined_result_dict = result.to_dict()

        processing_timestamp = combined_result_dict.get("processing_timestamp")
        if processing_timestamp is None:
            processing_timestamp = datetime.now(timezone.utc).isoformat()

        created_at = combined_result_dict.get("created_at")
        if created_at is None:
            created_at = datetime.now(timezone.utc).isoformat()

        updated_at = combined_result_dict.get("updated_at")
        if updated_at is None:
            updated_at = datetime.now(timezone.utc).isoformat()

        detection_info = combined_result_dict.get("detection", {})
        if not detection_info and result.detection_result:
            detection_info = {
                "request_id": result.detection_result.request_id,
                "status": result.detection_result.status,
                "processing_timestamp": result.detection_result.processing_timestamp.isoformat(),
                "summary": result.detection_result.summary,
                "image_result_url": result.detection_result.image_result_url,
            }

        response_data = {
            "combined_id": combined_result_dict.get("combined_id"),
            "image_id": combined_result_dict.get("image_id"),
            "user_id": combined_result_dict.get("user_id"),
            "status": combined_result_dict.get("status"),
            "total_processing_time_ms": result.total_processing_time_ms,
            "detection": detection_info,
            "results": result._merge_results(),
            "location": combined_result_dict.get("location"),
            "processing_timestamp": processing_timestamp,
            "created_at": created_at,
            "updated_at": updated_at,
            "summary": combined_result_dict.get("summary", {}),
        }

        return CombinedProcessingResponse(**response_data)

    except Exception as e:
        logger.exception(f"Erro ao recuperar resultados combinados: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao recuperar resultados combinados: {str(e)}")


@combined_router.get("/results/request/{request_id}", response_model=Optional[CombinedProcessingResponse])
async def get_results_by_request_id(
    request_id: str,
    combined_usecase: CombinedProcessingUseCase = Depends(get_combined_processing_usecase),
):
    try:
        result = await combined_usecase.get_result_by_request_id(request_id)

        if not result:
            return None

        combined_result_dict = result.to_dict()

        processing_timestamp = combined_result_dict.get("processing_timestamp")
        if processing_timestamp is None:
            processing_timestamp = datetime.now(timezone.utc).isoformat()

        created_at = combined_result_dict.get("created_at")
        if created_at is None:
            created_at = datetime.now(timezone.utc).isoformat()

        updated_at = combined_result_dict.get("updated_at")
        if updated_at is None:
            updated_at = datetime.now(timezone.utc).isoformat()

        detection_info = combined_result_dict.get("detection", {})
        if not detection_info and result.detection_result:
            detection_info = {
                "request_id": result.detection_result.request_id,
                "status": result.detection_result.status,
                "processing_timestamp": result.detection_result.processing_timestamp.isoformat(),
                "summary": result.detection_result.summary,
                "image_result_url": result.detection_result.image_result_url,
            }

        response_data = {
            "combined_id": combined_result_dict.get("combined_id"),
            "image_id": combined_result_dict.get("image_id"),
            "user_id": combined_result_dict.get("user_id"),
            "status": combined_result_dict.get("status"),
            "total_processing_time_ms": result.total_processing_time_ms,
            "detection": detection_info,
            "results": result._merge_results(),
            "location": combined_result_dict.get("location"),
            "processing_timestamp": processing_timestamp,
            "created_at": created_at,
            "updated_at": updated_at,
            "summary": combined_result_dict.get("summary", {}),
        }

        return CombinedProcessingResponse(**response_data)

    except Exception as e:
        logger.exception(f"Erro ao recuperar resultados pelo request_id: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao recuperar resultados pelo request_id: {str(e)}")
