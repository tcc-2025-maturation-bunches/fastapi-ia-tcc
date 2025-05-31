from fastapi import APIRouter, Depends, HTTPException

from src.modules.ia_integration.usecase.detect_usecase import DetectUseCase
from src.shared.domain.enums.ia_model_type_enum import ModelType
from src.shared.domain.models.http_models import ProcessImageRequest, ProcessingResponse

ia_router = APIRouter(prefix="/ia", tags=["IA"])


def get_detect_usecase():
    return DetectUseCase()


@ia_router.post("/process", response_model=ProcessingResponse)
async def process_image(
    request: ProcessImageRequest,
    detect_usecase: DetectUseCase = Depends(get_detect_usecase),
):
    """Processa uma imagem usando o modelo de IA selecionado."""
    try:
        metadata = None
        if request.metadata:
            try:
                metadata = request.metadata.model_dump()
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Erro ao processar metadados: {str(e)}")

        if request.model_type == ModelType.DETECTION:
            result = await detect_usecase.execute(
                image_url=str(request.image_url),
                user_id=request.user_id,
                metadata=metadata,
            )
        elif request.model_type == ModelType.COMBINED:
            raise HTTPException(
                status_code=400, detail="Para processamento combinado, use o endpoint /combined/process."
            )
        else:
            raise HTTPException(status_code=400, detail=f"Tipo de modelo inválido: {request.model_type}")

        response_data = result.to_dict()
        return ProcessingResponse(**response_data)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao processar imagem: {str(e)}")
