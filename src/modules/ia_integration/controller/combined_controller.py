import logging
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from src.app.config import settings
from src.modules.ia_integration.usecase.combined_processing_usecase import CombinedProcessingUseCase
from src.shared.domain.models.combined_models import CombinedContractResponse, CombinedProcessingRequest
from src.shared.domain.models.http_models import ProcessingStatusResponse
from src.shared.mappers.contract_mapper import ContractResponseMapper

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
        metadata = request.metadata if request.metadata else {}

        required_fields = ["user_id", "image_id", "location"]
        missing_fields = [field for field in required_fields if not metadata.get(field)]

        if missing_fields:
            raise HTTPException(
                status_code=400,
                detail=f"Os seguintes campos são obrigatórios nos metadados: {', '.join(missing_fields)}",
            )
        maturation_threshold = metadata.get("maturation_threshold") or settings.MIN_DETECTION_CONFIDENCE

        request_id = await combined_usecase.start_processing(
            image_url=str(request.image_url),
            result_upload_url=str(request.result_upload_url) if request.result_upload_url else None,
            metadata=metadata,
            maturation_threshold=maturation_threshold,
        )

        background_tasks.add_task(
            combined_usecase.execute_in_background,
            request_id=request_id,
            image_url=str(request.image_url),
            result_upload_url=str(request.result_upload_url) if request.result_upload_url else None,
            metadata=metadata,
            maturation_threshold=maturation_threshold,
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


@combined_router.get("/results/{image_id}", response_model=Optional[CombinedContractResponse])
async def get_combined_results(
    image_id: str,
    combined_usecase: CombinedProcessingUseCase = Depends(get_combined_processing_usecase),
):
    try:
        result = await combined_usecase.get_combined_result(image_id)

        if not result:
            return None

        return ContractResponseMapper.to_contract_response(result)

    except Exception as e:
        logger.exception(f"Erro ao recuperar resultados combinados: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao recuperar resultados combinados: {str(e)}")


@combined_router.get("/results/request/{request_id}", response_model=Optional[CombinedContractResponse])
async def get_results_by_request_id(
    request_id: str,
    combined_usecase: CombinedProcessingUseCase = Depends(get_combined_processing_usecase),
):
    try:
        result = await combined_usecase.get_result_by_request_id(request_id)

        if not result:
            raise HTTPException(status_code=404, detail=f"Resultado para request {request_id} não encontrado")

        return ContractResponseMapper.to_contract_response(result)

    except Exception as e:
        logger.exception(f"Erro ao recuperar resultados pelo request_id: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao recuperar resultados pelo request_id: {str(e)}")
