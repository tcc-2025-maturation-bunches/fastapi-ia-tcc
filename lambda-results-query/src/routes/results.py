import base64
import json
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from src.app.config import settings
from src.services.results_service import ResultsService
from src.utils.validator import validate_device_id, validate_request_id, validate_user_id

logger = logging.getLogger(__name__)

results_router = APIRouter()


class PaginatedResultsResponse(BaseModel):
    items: List[Dict[str, Any]]
    total_count: int
    has_more: bool
    next_page_token: Optional[str] = None
    current_page_size: int
    filters_applied: Dict[str, Any]


def get_results_service() -> ResultsService:
    return ResultsService()


@results_router.get("/request/{request_id}", response_model=Dict[str, Any])
async def get_result_by_request_id(request_id: str, results_service: ResultsService = Depends(get_results_service)):
    try:
        validate_request_id(request_id)
        result = await results_service.get_by_request_id(request_id)

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Resultado não encontrado para request_id: {request_id}",
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Erro ao recuperar resultado por request_id: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erro ao recuperar resultado")


@results_router.get("/image/{image_id}", response_model=List[Dict[str, Any]])
async def get_results_by_image_id(image_id: str, results_service: ResultsService = Depends(get_results_service)):
    try:
        results = await results_service.get_by_image_id(image_id)

        if not results:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Nenhum resultado encontrado para image_id: {image_id}",
            )

        return results

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Erro ao recuperar resultados por image_id: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erro ao recuperar resultados")


@results_router.get("/user/{user_id}", response_model=List[Dict[str, Any]])
async def get_results_by_user_id(
    user_id: str,
    limit: int = Query(settings.DEFAULT_PAGE_SIZE, ge=1, le=settings.MAX_QUERY_LIMIT),
    results_service: ResultsService = Depends(get_results_service),
):
    try:
        validate_user_id(user_id)
        results = await results_service.get_by_user_id(user_id, limit)

        if not results:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Nenhum resultado encontrado para user_id: {user_id}",
            )

        return results

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Erro ao recuperar resultados por user_id: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erro ao recuperar resultados")


@results_router.get("/device/{device_id}", response_model=List[Dict[str, Any]])
async def get_results_by_device_id(
    device_id: str,
    limit: int = Query(settings.DEFAULT_PAGE_SIZE, ge=1, le=settings.MAX_QUERY_LIMIT),
    results_service: ResultsService = Depends(get_results_service),
):
    try:
        validate_device_id(device_id)
        results = await results_service.get_by_device_id(device_id, limit)

        if not results:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Nenhum resultado encontrado para device_id: {device_id}",
            )

        return results

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Erro ao recuperar resultados por device_id: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erro ao recuperar resultados")


@results_router.get("/all", response_model=PaginatedResultsResponse)
async def get_all_results(
    limit: int = Query(settings.DEFAULT_PAGE_SIZE, ge=1, le=settings.MAX_QUERY_LIMIT),
    page_token: Optional[str] = Query(None, description="Token para paginação"),
    status_filter: Optional[str] = Query(None, description="Filtrar por status"),
    user_id: Optional[str] = Query(None, description="Filtrar por user_id"),
    device_id: Optional[str] = Query(None, description="Filtrar por device_id"),
    exclude_errors: bool = Query(False, description="Excluir resultados com erro"),
    results_service: ResultsService = Depends(get_results_service),
):
    try:
        last_evaluated_key = None
        if page_token:
            try:
                decoded_token = base64.b64decode(page_token.encode()).decode()
                last_evaluated_key = json.loads(decoded_token)
            except Exception as e:
                logger.warning(f"Token de página inválido: {e}")
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token de página inválido")

        validated_device_id = validate_device_id(device_id) if device_id else None

        result = await results_service.get_all_results(
            limit=limit,
            last_evaluated_key=last_evaluated_key,
            status_filter=status_filter,
            user_id=user_id,
            device_id=validated_device_id,
            exclude_errors=exclude_errors,
        )

        next_page_token = None
        if result["next_page_key"]:
            try:
                token_json = json.dumps(result["next_page_key"])
                next_page_token = base64.b64encode(token_json.encode()).decode()
            except Exception as e:
                logger.warning(f"Erro ao codificar token de página: {e}")

        return PaginatedResultsResponse(
            items=result["items"],
            total_count=result["total_count"],
            has_more=result["has_more"],
            next_page_token=next_page_token,
            current_page_size=len(result["items"]),
            filters_applied=result.get("filters_applied", {}),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Erro ao recuperar todos os resultados: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erro ao recuperar resultados")


@results_router.get("/summary", response_model=Dict[str, Any])
async def get_results_summary(
    days: int = Query(7, ge=1, le=365, description="Número de dias para análise"),
    device_id: Optional[str] = Query(None, description="Filtrar por device_id"),
    results_service: ResultsService = Depends(get_results_service),
):
    try:
        validated_device_id = validate_device_id(device_id) if device_id else None

        summary = await results_service.get_results_summary(days, device_id=validated_device_id)
        return summary

    except Exception as e:
        logger.exception(f"Erro ao gerar resumo dos resultados: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erro ao gerar resumo dos resultados"
        )


@results_router.get("/stats/user/{user_id}", response_model=Dict[str, Any])
async def get_user_stats(
    user_id: str,
    days: int = Query(30, ge=1, le=365, description="Número de dias para análise"),
    results_service: ResultsService = Depends(get_results_service),
):
    try:
        validate_user_id(user_id)
        stats = await results_service.get_user_statistics(user_id, days)
        return stats

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Erro ao obter estatísticas do usuário: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erro ao obter estatísticas do usuário"
        )
