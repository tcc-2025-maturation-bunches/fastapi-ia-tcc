import logging
from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException

from src.app.config import settings
from src.modules.status.usecase.health_check_usecase import HealthCheckUseCase
from src.shared.domain.models.status_models import HealthCheckResponse, ServiceStatusResponse

logger = logging.getLogger(__name__)

status_router = APIRouter(prefix="/status", tags=["System Status"])


def get_health_check_usecase():
    return HealthCheckUseCase()


@status_router.get("/health", response_model=HealthCheckResponse)
async def health_check(
    health_check_usecase: HealthCheckUseCase = Depends(get_health_check_usecase),
):
    try:
        health_status = await health_check_usecase.check_system_health()
        return health_status

    except Exception as e:
        logger.exception(f"Erro ao verificar status de saúde do sistema: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao verificar status de saúde do sistema: {str(e)}")


@status_router.get("/ai-service", response_model=ServiceStatusResponse)
async def check_ai_service(
    health_check_usecase: HealthCheckUseCase = Depends(get_health_check_usecase),
):
    try:
        ai_status = await health_check_usecase.check_ai_service()
        return ai_status

    except Exception as e:
        logger.exception(f"Erro ao verificar status do serviço de IA: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao verificar status do serviço de IA: {str(e)}")


@status_router.get("/config", response_model=Dict[str, Any])
async def get_api_config():
    public_config = {
        "environment": settings.ENVIRONMENT,
        "version": settings.APP_VERSION,
        "processing_options": {
            "enable_auto_maturation": settings.ENABLE_AUTO_MATURATION,
            "min_detection_confidence": settings.MIN_DETECTION_CONFIDENCE,
            "min_maturation_confidence": settings.MIN_MATURATION_CONFIDENCE,
        },
        "upload_options": {
            "max_upload_size_mb": settings.MAX_UPLOAD_SIZE_MB,
            "allowed_image_types": settings.ALLOWED_IMAGE_TYPES,
            "presigned_url_expiry_minutes": settings.PRESIGNED_URL_EXPIRY_MINUTES,
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    return public_config
