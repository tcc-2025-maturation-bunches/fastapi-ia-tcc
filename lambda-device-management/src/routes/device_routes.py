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


class StandardResponse(BaseModel):
    message: str
    device_id: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


@device_router.post(
    "/register",
    response_model=HeartbeatResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar novo dispositivo",
    description="Registra um novo dispositivo no sistema e retorna as configurações iniciais",
    tags=["registration"],
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
    "",
    response_model=List[DeviceResponse],
    status_code=status.HTTP_200_OK,
    summary="Listar todos os dispositivos",
    description="Lista todos os dispositivos com filtros opcionais por status e localização",
    tags=["listing"],
)
async def list_devices(
    status_filter: Optional[str] = Query(None, description="Filtrar por status (online, offline, maintenance, error)"),
    location_filter: Optional[str] = Query(None, description="Filtrar por localização"),
    limit: int = Query(50, ge=1, le=100, description="Limite de dispositivos retornados"),
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
    "/recent",
    response_model=List[DeviceResponse],
    status_code=status.HTTP_200_OK,
    summary="Listar dispositivos recentemente ativos",
    description="Lista dispositivos que estiveram ativos recentemente, ordenados por última atividade",
    tags=["listing"],
)
async def get_recently_active_devices(
    limit: int = Query(50, ge=1, le=100, description="Limite de dispositivos retornados")
):
    try:
        device_service = DeviceService()
        devices = await device_service.get_recently_active_devices(limit)

        return [DeviceResponse(**device.to_dict()) for device in devices]

    except Exception as e:
        logger.exception(f"Erro ao buscar dispositivos recentes: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Falha ao buscar dispositivos recentes"
        )


@device_router.get(
    "/by-status/{device_status}",
    response_model=List[DeviceResponse],
    status_code=status.HTTP_200_OK,
    summary="Listar dispositivos por status",
    description="Lista dispositivos filtrados por um status específico",
    tags=["listing"],
)
async def get_devices_by_status(
    device_status: str, limit: int = Query(100, ge=1, le=200, description="Limite de dispositivos retornados")
):
    try:
        if device_status not in ["online", "offline", "maintenance", "error", "pending"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Status deve ser: online, offline, maintenance, error ou pending",
            )

        device_service = DeviceService()
        devices = await device_service.get_devices_by_status(device_status, limit)

        return [DeviceResponse(**device.to_dict()) for device in devices]

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Erro ao buscar dispositivos por status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Falha ao buscar dispositivos por status"
        )


@device_router.get(
    "/{device_id}",
    response_model=DeviceResponse,
    status_code=status.HTTP_200_OK,
    summary="Obter detalhes do dispositivo",
    description="Obtém informações detalhadas de um dispositivo específico",
    tags=["details"],
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


@device_router.post(
    "/{device_id}/heartbeat",
    response_model=HeartbeatResponse,
    status_code=status.HTTP_200_OK,
    summary="Enviar heartbeat do dispositivo",
    description="Processa heartbeat de um dispositivo e retorna comandos e configurações pendentes",
    tags=["heartbeat"],
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
    response_model=StandardResponse,
    status_code=status.HTTP_200_OK,
    summary="Atualizar configuração do dispositivo",
    description="Atualiza a configuração específica de um dispositivo",
    tags=["configuration"],
)
async def update_device_config(device_id: str, config_update: DeviceConfigUpdate):
    try:
        validate_device_id(device_id)
        device_service = DeviceService()

        result = await device_service.update_device_config(device_id, config_update.model_dump(exclude_none=True))

        if not result:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Dispositivo {device_id} não encontrado")

        return StandardResponse(
            message="Configuração atualizada com sucesso", device_id=device_id, data={"updated_config": result}
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Erro ao atualizar configuração: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Falha ao atualizar configuração")


@device_router.post(
    "/global-config",
    response_model=StandardResponse,
    status_code=status.HTTP_200_OK,
    summary="Atualizar configuração global",
    description="Atualiza configurações que se aplicam a todos os dispositivos",
    tags=["configuration"],
)
async def update_global_config(config: GlobalConfigRequest):
    try:
        device_service = DeviceService()
        result = await device_service.update_global_config(config.model_dump())

        return StandardResponse(
            message="Configuração global atualizada com sucesso",
            data={"affected_devices": result.get("affected_devices", 0), "config": config.model_dump()},
        )

    except Exception as e:
        logger.exception(f"Erro ao atualizar configuração global: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Falha ao atualizar configuração global"
        )


@device_router.get(
    "/stats/overview",
    response_model=DeviceStatsResponse,
    status_code=status.HTTP_200_OK,
    summary="Obter estatísticas gerais dos dispositivos",
    description="Retorna estatísticas consolidadas de todos os dispositivos",
    tags=["statistics"],
)
async def get_device_stats():
    try:
        device_service = DeviceService()
        stats = await device_service.get_device_statistics()

        return DeviceStatsResponse(**stats)

    except Exception as e:
        logger.exception(f"Erro ao obter estatísticas: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Falha ao recuperar estatísticas")


@device_router.get(
    "/analytics/location/{location}",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Análise detalhada por localização",
    description="Retorna análise detalhada dos dispositivos em uma localização específica",
    tags=["analytics"],
)
async def get_location_analytics(location: str):
    try:
        device_service = DeviceService()
        analytics = await device_service.get_location_analytics(location)

        return analytics

    except Exception as e:
        logger.exception(f"Erro ao obter análise da localização: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Falha ao obter análise da localização"
        )


@device_router.post(
    "/{device_id}/processing-notification",
    response_model=StandardResponse,
    status_code=status.HTTP_200_OK,
    summary="Notificar conclusão de processamento",
    description="Notifica o sistema sobre a conclusão de processamento de um dispositivo",
    tags=["notifications"],
)
async def notify_processing_complete(device_id: str, notification: Dict[str, Any]):
    try:
        validate_device_id(device_id)
        device_service = DeviceService()

        await device_service.update_device_statistics(device_id, notification)

        return StandardResponse(message="Estatísticas atualizadas com sucesso", device_id=device_id)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Erro ao processar notificação: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Falha ao processar notificação")


@device_router.post(
    "/maintenance/check-offline",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Verificar dispositivos offline",
    description="Verifica e marca dispositivos que estão offline há muito tempo",
    tags=["maintenance"],
)
async def check_offline_devices():
    try:
        device_service = DeviceService()
        result = await device_service.check_offline_devices()

        return result

    except Exception as e:
        logger.exception(f"Erro ao verificar dispositivos offline: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Falha ao verificar dispositivos offline"
        )


@device_router.delete(
    "/{device_id}",
    response_model=StandardResponse,
    status_code=status.HTTP_200_OK,
    summary="Remover dispositivo",
    description="Remove permanentemente um dispositivo do sistema",
    tags=["management"],
)
async def delete_device(device_id: str):
    try:
        validate_device_id(device_id)
        device_service = DeviceService()

        success = await device_service.dynamo_repository.delete_device(device_id)

        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Dispositivo {device_id} não encontrado")

        return StandardResponse(message="Dispositivo removido com sucesso", device_id=device_id)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Erro ao remover dispositivo: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Falha ao remover dispositivo")
