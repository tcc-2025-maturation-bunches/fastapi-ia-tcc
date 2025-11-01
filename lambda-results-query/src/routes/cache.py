import logging
from functools import lru_cache
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from src.app.config import settings
from src.services.cache_service import CacheService

logger = logging.getLogger(__name__)

cache_router = APIRouter()


class CacheStatsResponse(BaseModel):
    total_keys: int
    expired_keys: int
    active_keys: int


class CacheClearResponse(BaseModel):
    success: bool
    message: str
    keys_removed: Optional[int] = None


@lru_cache()
def get_cache_service() -> CacheService:
    return CacheService(ttl_seconds=settings.CACHE_TTL_SECONDS)


@cache_router.get("/stats", response_model=CacheStatsResponse)
async def get_cache_stats(cache_service: CacheService = Depends(get_cache_service)) -> CacheStatsResponse:
    try:
        logger.info("Recuperando estatísticas do cache")
        stats = cache_service.get_stats()
        return CacheStatsResponse(**stats)
    except Exception as e:
        logger.exception(f"Erro ao recuperar estatísticas do cache: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao recuperar estatísticas do cache",
        )


@cache_router.delete("/clear", response_model=CacheClearResponse)
async def clear_all_cache(cache_service: CacheService = Depends(get_cache_service)) -> CacheClearResponse:
    try:
        logger.info("Limpando todo o cache")
        stats_before = cache_service.get_stats()
        keys_count = stats_before["total_keys"]

        await cache_service.clear_all()

        logger.info(f"Cache limpo com sucesso: {keys_count} chaves removidas")
        return CacheClearResponse(success=True, message="Cache limpo com sucesso", keys_removed=keys_count)
    except Exception as e:
        logger.exception(f"Erro ao limpar cache: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erro ao limpar cache")


@cache_router.delete("/clear/prefix", response_model=CacheClearResponse)
async def clear_cache_by_prefix(
    prefix: str = Query(..., description="Prefixo das chaves a serem removidas"),
    cache_service: CacheService = Depends(get_cache_service),
) -> CacheClearResponse:
    try:
        logger.info(f"Limpando cache com prefixo: {prefix}")

        keys_count = cache_service.count_keys_by_prefix(prefix)

        await cache_service.clear_prefix(prefix)

        logger.info(f"Cache limpo para prefixo {prefix}: {keys_count} chaves removidas")
        return CacheClearResponse(
            success=True,
            message=f"Cache limpo para prefixo '{prefix}'",
            keys_removed=keys_count,
        )
    except Exception as e:
        logger.exception(f"Erro ao limpar cache por prefixo: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao limpar cache por prefixo: {prefix}",
        )


@cache_router.delete("/clear/key", response_model=CacheClearResponse)
async def clear_cache_by_key(
    prefix: str = Query(..., description="Prefixo da chave"),
    cache_service: CacheService = Depends(get_cache_service),
    **kwargs: Any,
) -> CacheClearResponse:
    try:
        logger.info(f"Removendo chave específica do cache: {prefix}")

        key_exists = cache_service.key_exists(prefix, **kwargs)

        await cache_service.delete(prefix, **kwargs)

        if key_exists:
            logger.info(f"Chave removida do cache: {prefix}")
            return CacheClearResponse(success=True, message="Chave removida com sucesso", keys_removed=1)
        else:
            logger.info(f"Chave não encontrada no cache: {prefix}")
            return CacheClearResponse(success=True, message="Chave não encontrada no cache", keys_removed=0)
    except Exception as e:
        logger.exception(f"Erro ao remover chave do cache: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao remover chave do cache",
        )
