import logging
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
                logger.info(f"Dispositivo {request.device_id} já existe, atualizando heartbeat")
                previous_status = existing_device.status
                existing_device.update_heartbeat(status=request.status)
                await self.dynamo_repository.save_device(existing_device)

                await self._log_device_event(
                    existing_device,
                    "device_reconnected",
                    {"previous_status": previous_status, "new_status": request.status},
                )

                return {
                    "device_id": existing_device.device_id,
                    "status": existing_device.status,
                    "last_seen": existing_device.last_seen.isoformat(),
                    "config": existing_device.config,
                    "message": "Dispositivo já registrado, heartbeat atualizado",
                }

            device = Device(
                device_id=request.device_id,
                device_name=request.device_name,
                location=request.location,
                capabilities=request.capabilities.model_dump() if request.capabilities else {},
                status=request.status,
                last_seen=request.last_seen,
            )

            await self.dynamo_repository.save_device(device)

            await self._log_device_event(
                device, "device_registered", {"location": device.location, "capabilities": device.capabilities}
            )

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

            previous_status = device.status
            device.update_heartbeat(status=status, additional_data=additional_data)
            await self.dynamo_repository.save_device(device)

            if previous_status != status:
                await self._log_device_event(device, "status_changed", {"from": previous_status, "to": status})

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

            old_config = device.config.copy()
            device.update_config(config_updates)
            await self.dynamo_repository.save_device(device)

            await self._log_device_event(
                device,
                "config_updated",
                {"old_config": old_config, "new_config": device.config, "changes": config_updates},
            )

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

            success = processing_result.get("status") == "success"
            device.increment_capture_count(success=success)

            if processing_result.get("processing_time_ms"):
                current_avg = device.stats.get("average_processing_time_ms", 0)
                total_captures = device.stats.get("total_captures", 1)
                new_avg = (
                    (current_avg * (total_captures - 1)) + processing_result["processing_time_ms"]
                ) / total_captures
                device.stats["average_processing_time_ms"] = int(new_avg)

            await self.dynamo_repository.save_device(device)

            await self.dynamo_repository.save_device_stats(device)

            logger.info(f"Estatísticas atualizadas para dispositivo {device_id}")
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

    async def get_device_stats_history(self, device_id: str, days: int = 7) -> List[Dict[str, Any]]:
        try:
            stats_history = await self.dynamo_repository.get_device_stats_history(device_id, days)

            return [
                {
                    "date": item.get("date"),
                    "total_captures": item.get("total_captures", 0),
                    "successful_captures": item.get("successful_captures", 0),
                    "failed_captures": item.get("failed_captures", 0),
                    "success_rate": (
                        0
                        if item.get("total_captures", 0) == 0
                        else (item.get("successful_captures", 0) / item.get("total_captures", 0) * 100)
                    ),
                    "average_processing_time_ms": item.get("average_processing_time_ms", 0),
                }
                for item in stats_history
            ]

        except Exception as e:
            logger.exception(f"Erro ao obter histórico de estatísticas: {e}")
            raise

    async def get_device_activity(self, device_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        try:
            events = await self.dynamo_repository.get_device_events(device_id, limit)

            return [
                {
                    "timestamp": event.get("timestamp"),
                    "event_type": event.get("event_type"),
                    "event_data": event.get("event_data", {}),
                }
                for event in events
            ]

        except Exception as e:
            logger.exception(f"Erro ao obter atividades do dispositivo: {e}")
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

                    await self._log_device_event(
                        device, "global_config_applied", {"config_updates": device_config_updates}
                    )

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

                    await self._log_device_event(
                        device, "device_offline_detected", {"timeout_minutes": timeout_minutes}
                    )

                    offline_device_ids.append(device.device_id)

            if offline_device_ids:
                logger.warning(f"Dispositivos detectados como offline: {offline_device_ids}")

            return offline_device_ids

        except Exception as e:
            logger.exception(f"Erro ao verificar dispositivos offline: {e}")
            raise

    async def _log_device_event(self, device: Device, event_type: str, event_data: Dict[str, Any]) -> bool:
        try:
            return await self.dynamo_repository.save_device_event(device, event_type, event_data)
        except Exception as e:
            logger.warning(f"Falha ao registrar evento {event_type}: {e}")
            return False

    async def _get_pending_commands(self, device_id: str) -> List[Dict[str, Any]]:
        return []

    async def _get_config_updates(self, device_id: str) -> Optional[Dict[str, Any]]:
        return None
