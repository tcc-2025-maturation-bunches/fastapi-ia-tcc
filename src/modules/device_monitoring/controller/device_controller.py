import logging
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from src.modules.device_monitoring.usecase.device_analytics_usecase import DeviceAnalyticsUseCase
from src.modules.device_monitoring.usecase.device_monitoring_usecase import DeviceMonitoringUseCase
from src.modules.device_monitoring.usecase.device_query_usecase import DeviceQueryUseCase
from src.modules.device_monitoring.usecase.device_registration_usecase import DeviceRegistrationUseCase
from src.modules.device_monitoring.usecase.device_setup_usecase import DeviceSetupUseCase

logger = logging.getLogger(__name__)

monitoring_router = APIRouter(prefix="/devices", tags=["Device Monitoring"])


class DeviceRegistrationRequest(BaseModel):
    device_id: str
    device_name: str
    location: str
    capabilities: Dict[str, Any]


class DeviceHeartbeatRequest(BaseModel):
    device_id: str
    status: str
    last_seen: Optional[datetime] = None
    additional_data: Optional[Dict[str, Any]] = None


class DeviceConfigRequest(BaseModel):
    device_name: str
    location: str
    device_type: str
    capture_interval: int


class DeviceController:
    def __init__(self):
        self.monitoring_usecase = DeviceMonitoringUseCase()
        self.registration_usecase = DeviceRegistrationUseCase()
        self.query_usecase = DeviceQueryUseCase()
        self.setup_usecase = DeviceSetupUseCase()
        self.analytics_usecase = DeviceAnalyticsUseCase()


device_controller = DeviceController()


@monitoring_router.post("/register")
async def register_device(request: DeviceRegistrationRequest):
    """Registra um novo dispositivo no sistema"""
    try:
        device = await device_controller.registration_usecase.register_device(
            request.device_id, request.device_name, request.location, request.capabilities
        )

        return {
            "success": True,
            "message": "Dispositivo registrado com sucesso",
            "device": {
                "device_id": device.device_id,
                "device_name": device.device_name,
                "location": device.location,
                "status": device.status,
                "capabilities": device.capabilities,
            },
        }
    except Exception as e:
        logger.exception(f"Erro ao registrar dispositivo: {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")


@monitoring_router.post("/heartbeat")
async def update_heartbeat(request: DeviceHeartbeatRequest):
    """Atualiza o heartbeat de um dispositivo"""
    try:
        success = await device_controller.monitoring_usecase.update_device_heartbeat(
            request.device_id, request.status, request.last_seen, request.additional_data
        )

        if not success:
            raise HTTPException(status_code=404, detail="Dispositivo não encontrado")

        return {"success": True, "message": "Heartbeat atualizado com sucesso"}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Erro ao atualizar heartbeat: {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")


@monitoring_router.get("/")
async def list_devices(
    status: Optional[str] = Query(None, description="Filtrar por status"),
    location: Optional[str] = Query(None, description="Filtrar por localização"),
):
    """Lista todos os dispositivos com filtros opcionais"""
    try:
        devices = await device_controller.query_usecase.list_devices(status, location)

        return {
            "success": True,
            "count": len(devices),
            "devices": [
                {
                    "device_id": device.device_id,
                    "device_name": device.device_name,
                    "location": device.location,
                    "status": device.status,
                    "last_seen": device.last_seen.isoformat() if device.last_seen else None,
                    "capabilities": device.capabilities,
                    "stats": device.stats,
                }
                for device in devices
            ],
        }
    except Exception as e:
        logger.exception(f"Erro ao listar dispositivos: {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")


@monitoring_router.get("/{device_id}")
async def get_device(device_id: str):
    """Obtém detalhes de um dispositivo específico"""
    try:
        device = await device_controller.query_usecase.get_device(device_id)

        if not device:
            raise HTTPException(status_code=404, detail="Dispositivo não encontrado")

        return {
            "success": True,
            "device": {
                "device_id": device.device_id,
                "device_name": device.device_name,
                "location": device.location,
                "status": device.status,
                "last_seen": device.last_seen.isoformat() if device.last_seen else None,
                "created_at": device.created_at.isoformat() if device.created_at else None,
                "updated_at": device.updated_at.isoformat() if device.updated_at else None,
                "capabilities": device.capabilities,
                "stats": device.stats,
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Erro ao obter dispositivo: {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")


@monitoring_router.delete("/{device_id}")
async def unregister_device(device_id: str):
    """Remove um dispositivo do sistema"""
    try:
        success = await device_controller.registration_usecase.unregister_device(device_id)

        if not success:
            raise HTTPException(status_code=404, detail="Dispositivo não encontrado")

        return {"success": True, "message": "Dispositivo removido com sucesso"}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Erro ao remover dispositivo: {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")


@monitoring_router.put("/{device_id}/status")
async def update_device_status(device_id: str, status: str):
    """Atualiza o status de um dispositivo"""
    try:
        success = await device_controller.monitoring_usecase.update_device_status(device_id, status)

        if not success:
            raise HTTPException(status_code=404, detail="Dispositivo não encontrado")

        return {"success": True, "message": f"Status do dispositivo atualizado para: {status}"}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Erro ao atualizar status: {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")


@monitoring_router.get("/offline/check")
async def check_offline_devices(timeout_minutes: int = Query(5, description="Timeout em minutos")):
    """Verifica e atualiza dispositivos offline"""
    try:
        updated_count = await device_controller.monitoring_usecase.check_and_update_offline_devices(timeout_minutes)

        return {
            "success": True,
            "message": f"{updated_count} dispositivos marcados como offline",
            "updated_count": updated_count,
        }
    except Exception as e:
        logger.exception(f"Erro ao verificar dispositivos offline: {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")


@monitoring_router.get("/analytics/dashboard")
async def get_dashboard_data():
    """Obtém dados para o dashboard de monitoramento"""
    try:
        dashboard_data = await device_controller.query_usecase.get_dashboard_data()

        return {"success": True, "data": dashboard_data}
    except Exception as e:
        logger.exception(f"Erro ao obter dados do dashboard: {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")


@monitoring_router.get("/analytics/fleet")
async def get_fleet_analytics(days: int = Query(7, description="Número de dias para análise")):
    """Obtém analytics da frota completa"""
    try:
        analytics = await device_controller.analytics_usecase.get_fleet_analytics(days)

        return {"success": True, "analytics": analytics}
    except Exception as e:
        logger.exception(f"Erro ao obter analytics da frota: {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")


@monitoring_router.get("/{device_id}/analytics")
async def get_device_analytics(device_id: str, days: int = Query(7, description="Número de dias para análise")):
    """Obtém analytics de um dispositivo específico"""
    try:
        analytics = await device_controller.analytics_usecase.get_device_statistics(device_id, days)

        if not analytics:
            raise HTTPException(status_code=404, detail="Dispositivo não encontrado ou sem dados")

        return {"success": True, "analytics": analytics}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Erro ao obter analytics do dispositivo: {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")


@monitoring_router.get("/{device_id}/health")
async def get_device_health(device_id: str):
    """Obtém relatório de saúde de um dispositivo"""
    try:
        health_report = await device_controller.analytics_usecase.get_health_report(device_id)

        if not health_report:
            raise HTTPException(status_code=404, detail="Dispositivo não encontrado")

        return {"success": True, "health_report": health_report}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Erro ao obter relatório de saúde: {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")


@monitoring_router.post("/setup/config")
async def generate_device_config(request: DeviceConfigRequest):
    """Gera configuração para um novo dispositivo"""
    try:
        config = await device_controller.setup_usecase.generate_device_config(
            request.device_name, request.location, request.device_type, request.capture_interval
        )

        return {"success": True, "message": "Configuração gerada com sucesso", "config": config}
    except Exception as e:
        logger.exception(f"Erro ao gerar configuração: {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")


@monitoring_router.get("/analytics/location/{location}")
async def get_location_analytics(location: str, days: int = Query(7, description="Número de dias para análise")):
    """Obtém analytics de uma localização específica"""
    try:
        analytics = await device_controller.analytics_usecase.get_location_analytics(location, days)

        return {"success": True, "analytics": analytics}
    except Exception as e:
        logger.exception(f"Erro ao obter analytics da localização: {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")


@monitoring_router.get("/{device_id}/trends")
async def get_performance_trends(device_id: str, days: int = Query(30, description="Número de dias para análise")):
    """Obtém tendências de performance de um dispositivo"""
    try:
        trends = await device_controller.analytics_usecase.get_performance_trends(device_id, days)

        if not trends:
            raise HTTPException(status_code=404, detail="Dispositivo não encontrado ou sem dados suficientes")

        return {"success": True, "trends": trends}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Erro ao obter tendências: {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")
