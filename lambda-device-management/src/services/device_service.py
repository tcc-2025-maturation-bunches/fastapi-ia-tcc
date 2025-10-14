import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fruit_detection_shared.domain.entities import Device
from fruit_detection_shared.domain.models.device_models import DeviceRegistrationRequest

from src.app.config import settings
from src.repository.dynamo_repository import DynamoRepository

logger = logging.getLogger(__name__)


class DeviceService:
    def __init__(self, dynamo_repository: Optional[DynamoRepository] = None):
        self.dynamo_repository = dynamo_repository or DynamoRepository()

    async def register_new_device(self, request: DeviceRegistrationRequest) -> Dict[str, Any]:
        try:
            existing_device = await self.dynamo_repository.get_device_by_id(request.device_id)

            if existing_device:
                logger.info(f"Dispositivo {request.device_id} já existe. Registro ignorado.")
                raise ValueError(f"Dispositivo {request.device_id} já registrado")

            device = Device(
                device_id=request.device_id,
                device_name=request.device_name,
                location=request.location,
                capabilities=request.capabilities.model_dump() if request.capabilities else {},
                status=request.status,
                last_seen=request.last_seen,
            )

            await self.dynamo_repository.save_device(device)

            logger.info(f"Dispositivo {request.device_id} registrado com sucesso")

            return {
                "device_id": device.device_id,
                "status": device.status,
                "last_seen": device.last_seen.isoformat(),
                "config": device.config,
                "message": "Dispositivo registrado com sucesso",
            }

        except Exception as e:
            logger.exception(f"Erro ao registrar dispositivo {request.device_id}: {e}")
            raise

    async def process_heartbeat(
        self, device_id: str, status: str, additional_data: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        try:
            device = await self.dynamo_repository.get_device_by_id(device_id)

            if not device:
                logger.warning(f"Dispositivo {device_id} não encontrado para heartbeat")
                return None

            device.update_heartbeat(status=status, additional_data=additional_data)
            await self.dynamo_repository.save_device(device)

            logger.debug(f"Heartbeat processado para dispositivo {device_id}")

            pending_commands = await self._get_pending_commands(device_id)
            config_updates = await self._get_config_updates(device_id)

            return {
                "device_id": device.device_id,
                "status": device.status,
                "last_seen": device.last_seen.isoformat(),
                "commands": pending_commands,
                "config_updates": config_updates,
            }

        except Exception as e:
            logger.exception(f"Erro ao processar heartbeat para dispositivo {device_id}: {e}")
            raise

    async def get_device_by_id(self, device_id: str) -> Optional[Device]:
        try:
            return await self.dynamo_repository.get_device_by_id(device_id)
        except Exception as e:
            logger.exception(f"Erro ao obter dispositivo {device_id}: {e}")
            raise

    async def list_devices(
        self,
        status_filter: Optional[str] = None,
        location_filter: Optional[str] = None,
        limit: int = 50,
    ) -> List[Device]:
        try:
            return await self.dynamo_repository.list_devices(
                status_filter=status_filter, location_filter=location_filter, limit=limit
            )
        except Exception as e:
            logger.exception(f"Erro ao listar dispositivos: {e}")
            raise

    async def update_device_config(self, device_id: str, config_updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            device = await self.dynamo_repository.get_device_by_id(device_id)

            if not device:
                logger.warning(f"Dispositivo {device_id} não encontrado para atualização de config")
                return None

            device.update_config(config_updates)
            await self.dynamo_repository.save_device(device)

            logger.info(f"Configuração atualizada para dispositivo {device_id}")

            return device.config

        except Exception as e:
            logger.exception(f"Erro ao atualizar configuração do dispositivo {device_id}: {e}")
            raise

    async def update_device_statistics(self, device_id: str, processing_result: Dict[str, Any]) -> bool:
        try:
            device = await self.dynamo_repository.get_device_by_id(device_id)

            if not device:
                logger.warning(f"Dispositivo {device_id} não encontrado para atualização de estatísticas")
                return False

            success = processing_result.get("success", False)
            device.increment_capture_count(success=success)

            if processing_result.get("processing_time_ms"):
                current_avg = device.stats.get("average_processing_time_ms", 0)
                total_captures = device.stats.get("total_captures", 1)
                new_avg = (
                    (current_avg * (total_captures - 1)) + processing_result["processing_time_ms"]
                ) / total_captures
                device.stats["average_processing_time_ms"] = int(new_avg)

            await self.dynamo_repository.save_device(device)

            logger.info(f"Estatísticas atualizadas para dispositivo {device_id} - Success: {success}")
            return True

        except Exception as e:
            logger.exception(f"Erro ao atualizar estatísticas do dispositivo {device_id}: {e}")
            raise

    async def get_device_statistics(self) -> Dict[str, Any]:
        try:
            devices = await self.dynamo_repository.list_devices(limit=1000)

            total_devices = len(devices)
            online_devices = sum(1 for d in devices if d.status == "online")
            offline_devices = sum(1 for d in devices if d.status == "offline")
            maintenance_devices = sum(1 for d in devices if d.status == "maintenance")
            error_devices = sum(1 for d in devices if d.status == "error")

            devices_by_location = {}
            for device in devices:
                location = device.location
                devices_by_location[location] = devices_by_location.get(location, 0) + 1

            recent_registrations = []
            for device in sorted(devices, key=lambda d: d.created_at, reverse=True)[:5]:
                recent_registrations.append(
                    {
                        "device_id": device.device_id,
                        "device_name": device.device_name,
                        "location": device.location,
                        "status": device.status,
                        "created_at": device.created_at.isoformat(),
                    }
                )

            return {
                "total_devices": total_devices,
                "online_devices": online_devices,
                "offline_devices": offline_devices,
                "maintenance_devices": maintenance_devices,
                "error_devices": error_devices,
                "devices_by_location": devices_by_location,
                "recent_registrations": recent_registrations,
            }

        except Exception as e:
            logger.exception(f"Erro ao obter estatísticas dos dispositivos: {e}")
            raise

    async def update_global_config(self, global_config: Dict[str, Any]) -> Dict[str, Any]:
        try:
            devices = await self.dynamo_repository.list_devices(status_filter="online", limit=1000)

            affected_devices = 0
            config_mapping = {
                "min_capture_interval": "capture_interval",
                "image_quality": "image_quality",
                "max_resolution": "image_resolution",
                "min_detection_confidence": "detection_confidence",
                "min_maturation_confidence": "maturation_confidence",
            }

            device_config_updates = {}
            for global_key, device_key in config_mapping.items():
                if global_key in global_config:
                    device_config_updates[device_key] = global_config[global_key]

            if device_config_updates:
                for device in devices:
                    device.update_config(device_config_updates)
                    await self.dynamo_repository.save_device(device)
                    affected_devices += 1

            logger.info(f"Configuração global aplicada a {affected_devices} dispositivos")

            return {"affected_devices": affected_devices, "updated_config": device_config_updates}

        except Exception as e:
            logger.exception(f"Erro ao atualizar configuração global: {e}")
            raise

    async def check_offline_devices(self) -> List[str]:
        try:
            devices = await self.dynamo_repository.list_devices(status_filter="online", limit=1000)

            offline_device_ids = []
            timeout_minutes = settings.HEARTBEAT_TIMEOUT_MINUTES

            for device in devices:
                if not device.is_online(timeout_minutes=timeout_minutes):
                    device.status = "offline"
                    await self.dynamo_repository.save_device(device)
                    offline_device_ids.append(device.device_id)

            if offline_device_ids:
                logger.warning(f"Dispositivos detectados como offline: {offline_device_ids}")

            return offline_device_ids

        except Exception as e:
            logger.exception(f"Erro ao verificar dispositivos offline: {e}")
            raise

    async def _get_pending_commands(self, device_id: str) -> List[Dict[str, Any]]:
        return []

    async def _get_config_updates(self, device_id: str) -> Optional[Dict[str, Any]]:
        return None

    async def get_devices_by_status(self, status: str, limit: int = 100) -> List[Device]:
        try:
            return await self.dynamo_repository.get_devices_by_status(status, limit)
        except Exception as e:
            logger.exception(f"Erro ao obter dispositivos por status {status}: {e}")
            raise

    async def get_recently_active_devices(self, limit: int = 50) -> List[Device]:
        try:
            return await self.dynamo_repository.get_recently_active_devices(limit)
        except Exception as e:
            logger.exception(f"Erro ao obter dispositivos recentes: {e}")
            raise

    async def get_location_analytics(self, location: str) -> Dict[str, Any]:
        try:
            devices = await self.dynamo_repository.get_devices_by_location(location)

            status_counts = {}
            for device in devices:
                status_counts[device.status] = status_counts.get(device.status, 0) + 1

            active_devices = sorted(
                [d for d in devices if d.stats and d.stats.get("total_captures", 0) > 0],
                key=lambda d: d.stats.get("total_captures", 0),
                reverse=True,
            )[:5]

            now = datetime.now(timezone.utc)
            recent_activity = sum(1 for d in devices if d.last_seen and (now - d.last_seen).total_seconds() < 3600)

            return {
                "location": location,
                "total_devices": len(devices),
                "status_breakdown": status_counts,
                "recent_activity_count": recent_activity,
                "top_active_devices": [
                    {
                        "device_id": d.device_id,
                        "device_name": d.device_name,
                        "total_captures": d.stats.get("total_captures", 0),
                        "last_seen": d.last_seen.isoformat() if d.last_seen else None,
                    }
                    for d in active_devices
                ],
                "average_captures": (
                    sum(d.stats.get("total_captures", 0) for d in devices) / len(devices) if devices else 0
                ),
            }

        except Exception as e:
            logger.exception(f"Erro ao obter análise da localização {location}: {e}")
            raise
