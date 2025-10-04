import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, status
from fruit_detection_shared.domain.models.device_models import (
    DeviceConfigUpdate,
    DeviceRegistrationRequest,
    DeviceResponse,
    GlobalConfigRequest,
)
from pydantic import BaseModel, Field

from src.services.device_service import DeviceService
from src.utils.validators import validate_device_id

logger = logging.getLogger(__name__)

device_router = APIRouter()


class HeartbeatRequest(BaseModel):
    status: str = Field("online", pattern="^(online|offline|maintenance|error)$")
    additional_data: Optional[Dict[str, Any]] = None


class HeartbeatResponse(BaseModel):
    device_id: str
    status: str
    last_seen: datetime
    commands: List[Dict[str, Any]] = []
    config_updates: Optional[Dict[str, Any]] = None
    message: str


class DeviceStatsResponse(BaseModel):
    total_devices: int
    online_devices: int
    offline_devices: int
    maintenance_devices: int
    error_devices: int
    devices_by_location: Dict[str, int]
    recent_registrations: List[Dict[str, Any]]


@device_router.post(
    "/register",
    response_model=HeartbeatResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar novo dispositivo",
)
async def register_device(request: DeviceRegistrationRequest):
    try:
        validate_device_id(request.device_id)
        logger.info(f"Registrando dispositivo: {request.device_id}")

        device_service = DeviceService()
        result = await device_service.register_new_device(request)

        return HeartbeatResponse(
            device_id=request.device_id,
            status=result["status"],
            last_seen=datetime.fromisoformat(result["last_seen"]),
            commands=[],
            config_updates=result.get("config"),
            message="Dispositivo registrado com sucesso",
        )

    except ValueError as e:
        logger.warning(f"Dados de registro inválidos: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.exception(f"Erro ao registrar dispositivo: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Falha ao registrar dispositivo")


@device_router.get(
    "/all",
    response_model=List[DeviceResponse],
    status_code=status.HTTP_200_OK,
    summary="Listar todos os dispositivos",
)
async def list_devices(
    status_filter: Optional[str] = Query(None, description="Filtrar por status"),
    location_filter: Optional[str] = Query(None, description="Filtrar por localização"),
    limit: int = Query(50, ge=1, le=100),
):
    try:
        device_service = DeviceService()
        devices = await device_service.list_devices(
            status_filter=status_filter, location_filter=location_filter, limit=limit
        )

        return [DeviceResponse(**device.to_dict()) for device in devices]

    except Exception as e:
        logger.exception(f"Erro ao listar dispositivos: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Falha ao listar dispositivos")


@device_router.get(
    "/stats",
    response_model=DeviceStatsResponse,
    status_code=status.HTTP_200_OK,
    summary="Obter estatísticas dos dispositivos",
)
async def get_device_stats():
    try:
        device_service = DeviceService()
        stats = await device_service.get_device_statistics()

        return DeviceStatsResponse(**stats)

    except Exception as e:
        logger.exception(f"Erro ao obter estatísticas: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Falha ao recuperar estatísticas")


@device_router.post(
    "/global-config",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Atualizar configuração global",
)
async def update_global_config(config: GlobalConfigRequest):
    try:
        device_service = DeviceService()
        result = await device_service.update_global_config(config.model_dump())

        return {
            "message": "Configuração global atualizada com sucesso",
            "affected_devices": result.get("affected_devices", 0),
            "config": config.model_dump(),
        }

    except Exception as e:
        logger.exception(f"Erro ao atualizar configuração global: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Falha ao atualizar configuração global"
        )


@device_router.post(
    "/{device_id}/heartbeat",
    response_model=HeartbeatResponse,
    status_code=status.HTTP_200_OK,
    summary="Enviar heartbeat do dispositivo",
)
async def send_heartbeat(device_id: str, request: HeartbeatRequest):
    try:
        validate_device_id(device_id)
        logger.info(f"Heartbeat recebido do dispositivo: {device_id}")

        device_service = DeviceService()
        result = await device_service.process_heartbeat(device_id, request.status, request.additional_data)

        if not result:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Dispositivo {device_id} não encontrado")

        return HeartbeatResponse(
            device_id=device_id,
            status=result["status"],
            last_seen=datetime.fromisoformat(result["last_seen"]),
            commands=result.get("commands", []),
            config_updates=result.get("config_updates"),
            message="Heartbeat processado com sucesso",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Erro ao processar heartbeat: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Falha ao processar heartbeat")


@device_router.put(
    "/{device_id}/config",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Atualizar configuração do dispositivo",
)
async def update_device_config(device_id: str, config_update: DeviceConfigUpdate):
    try:
        validate_device_id(device_id)
        device_service = DeviceService()

        result = await device_service.update_device_config(device_id, config_update.model_dump(exclude_none=True))

        if not result:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Dispositivo {device_id} não encontrado")

        return {"message": "Configuração atualizada com sucesso", "device_id": device_id, "updated_config": result}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Erro ao atualizar configuração: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Falha ao atualizar configuração")


@device_router.post(
    "/{device_id}/processing-notification",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Notificar conclusão de processamento",
)
async def notify_processing_complete(device_id: str, notification: Dict[str, Any]):
    try:
        validate_device_id(device_id)
        device_service = DeviceService()

        await device_service.update_device_statistics(device_id, notification)

        return {"message": "Estatísticas atualizadas com sucesso", "device_id": device_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Erro ao processar notificação: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Falha ao processar notificação")


@device_router.get(
    "/{device_id}",
    response_model=DeviceResponse,
    status_code=status.HTTP_200_OK,
    summary="Obter detalhes do dispositivo",
)
async def get_device(device_id: str):
    try:
        validate_device_id(device_id)
        device_service = DeviceService()
        device = await device_service.get_device_by_id(device_id)

        if not device:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Dispositivo {device_id} não encontrado")

        return DeviceResponse(**device.to_dict())

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Erro ao obter dispositivo: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Falha ao recuperar dispositivo")
