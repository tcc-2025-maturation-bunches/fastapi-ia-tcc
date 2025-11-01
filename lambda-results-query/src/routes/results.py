import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from src.app.config import settings
from src.models.filter_models import DateRangeFilter
from src.models.stats_models import InferenceStatsResponse
from src.services.results_service import ResultsService
from src.utils.validator import validate_device_id, validate_request_id, validate_user_id

logger = logging.getLogger(__name__)

results_router = APIRouter()


class PaginatedResultsResponse(BaseModel):
    items: List[Dict[str, Any]]
    total_count: int
    total_pages: int
    current_page: int
    page_size: int
    has_previous: bool
    has_next: bool
    filters_applied: Dict[str, Any]


class CursorBasedResultsResponse(BaseModel):
    items: List[Dict[str, Any]]
    next_cursor: Optional[str]
    has_more: bool
    count: int
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
    page: int = Query(1, ge=1, description="Número da página (começando em 1)"),
    page_size: int = Query(
        settings.DEFAULT_PAGE_SIZE, ge=1, le=settings.MAX_QUERY_LIMIT, description="Itens por página"
    ),
    status_filter: Optional[str] = Query(None, description="Filtrar por status"),
    user_id: Optional[str] = Query(None, description="Filtrar por user_id"),
    device_id: Optional[str] = Query(None, description="Filtrar por device_id"),
    start_date: Optional[datetime] = Query(
        None, description="Data inicial (ISO 8601: YYYY-MM-DD ou YYYY-MM-DDTHH:MM:SS)"
    ),
    end_date: Optional[datetime] = Query(None, description="Data final (ISO 8601: YYYY-MM-DD ou YYYY-MM-DDTHH:MM:SS)"),
    exclude_errors: bool = Query(False, description="Excluir resultados com erro"),
    results_service: ResultsService = Depends(get_results_service),
):
    try:
        validated_device_id = validate_device_id(device_id) if device_id else None

        date_range_filter = DateRangeFilter(start_date=start_date, end_date=end_date)

        result = await results_service.get_all_results(
            page=page,
            page_size=page_size,
            status_filter=status_filter,
            user_id=user_id,
            device_id=validated_device_id,
            start_date=date_range_filter.start_date,
            end_date=date_range_filter.end_date,
            exclude_errors=exclude_errors,
        )

        return PaginatedResultsResponse(
            items=result["items"],
            total_count=result["total_count"],
            total_pages=result["total_pages"],
            current_page=result["current_page"],
            page_size=result["page_size"],
            has_previous=result["has_previous"],
            has_next=result["has_next"],
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


@results_router.get(
    "/stats/inference",
    response_model=InferenceStatsResponse,
    summary="Obter estatísticas de inferência para gráficos",
    description="Agrega os resultados de inferência dos últimos N dias para alimentar os gráficos de maturação.",
    tags=["Statistics", "Inference"],
)
async def get_inference_stats(
    days: int = Query(7, ge=1, le=90, description="Número de dias para incluir na análise"),
    results_service: ResultsService = Depends(get_results_service),
):
    try:
        stats = await results_service.get_inference_stats(days=days)
        return stats
    except Exception as e:
        logger.exception(f"Erro ao gerar estatísticas de inferência: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao gerar estatísticas de inferência: {str(e)}",
        )


@results_router.get("/all-cursor", response_model=CursorBasedResultsResponse)
async def get_all_results_cursor(
    cursor: Optional[str] = Query(None, description="Cursor para a página seguinte"),
    page_size: int = Query(
        settings.DEFAULT_PAGE_SIZE, ge=1, le=settings.MAX_QUERY_LIMIT, description="Itens por página"
    ),
    status_filter: Optional[str] = Query(None, description="Filtrar por status"),
    user_id: Optional[str] = Query(None, description="Filtrar por user_id"),
    device_id: Optional[str] = Query(None, description="Filtrar por device_id"),
    start_date: Optional[datetime] = Query(
        None, description="Data inicial (ISO 8601: YYYY-MM-DD ou YYYY-MM-DDTHH:MM:SS)"
    ),
    end_date: Optional[datetime] = Query(None, description="Data final (ISO 8601: YYYY-MM-DD ou YYYY-MM-DDTHH:MM:SS)"),
    exclude_errors: bool = Query(False, description="Excluir resultados com erro"),
    results_service: ResultsService = Depends(get_results_service),
):
    try:
        validated_device_id = validate_device_id(device_id) if device_id else None

        date_range_filter = DateRangeFilter(start_date=start_date, end_date=end_date)

        result = await results_service.get_all_results_cursor_based(
            limit=page_size,
            cursor=cursor,
            status_filter=status_filter,
            user_id=user_id,
            device_id=validated_device_id,
            start_date=date_range_filter.start_date,
            end_date=date_range_filter.end_date,
            exclude_errors=exclude_errors,
        )

        return CursorBasedResultsResponse(
            items=result["items"],
            next_cursor=result.get("next_cursor"),
            has_more=result["has_more"],
            count=result["count"],
            filters_applied=result.get("filters_applied", {}),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Erro ao recuperar todos os resultados com cursor: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erro ao recuperar resultados")
