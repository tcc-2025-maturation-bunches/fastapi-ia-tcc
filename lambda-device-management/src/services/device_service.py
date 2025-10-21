import logging
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any, Dict, List, Optional

from fruit_detection_shared.domain.entities import Device
from fruit_detection_shared.domain.models.device_models import DeviceRegistrationRequest

from src.app.config import settings
from src.repository.dynamo_repository import DynamoRepository

logger = logging.getLogger(__name__)


def get_current_minute_timestamp():
    now = datetime.now(timezone.utc)
    return now.replace(second=0, microsecond=0)


@lru_cache(maxsize=128)
async def get_device_by_id_cached(
    device_id: str, dynamo_repository: DynamoRepository, ttl_hash: datetime
) -> Optional[Device]:
    try:
        return await dynamo_repository.get_device_by_id(device_id)
    except Exception as e:
        logger.exception(f"Erro ao obter dispositivo (cache): {e}")
        raise


class DeviceService:
    def __init__(self, dynamo_repository: Optional[DynamoRepository] = None):
        self.dynamo_repository = dynamo_repository or DynamoRepository()

    async def register_new_device(self, request: DeviceRegistrationRequest) -> Dict[str, Any]:
        try:
            existing_device = await self.dynamo_repository.get_device_by_id(request.device_id)

            if existing_device:
                logger.info(f"Dispositivo {request.device_id} já existe")
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
            logger.info(f"Dispositivo {request.device_id} registrado")

            return {
                "device_id": device.device_id,
                "status": device.status,
                "last_seen": device.last_seen.isoformat(),
                "config": device.config,
                "message": "Dispositivo registrado com sucesso",
            }
        except Exception as e:
            logger.exception(f"Erro ao registrar dispositivo: {e}")
            raise

    async def process_heartbeat(
        self, device_id: str, status: str, additional_data: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        try:
            device = await self.dynamo_repository.get_device_by_id(device_id)

            if not device:
                logger.warning(f"Dispositivo {device_id} não encontrado para heartbeat")
                return None

            now = datetime.now(timezone.utc).isoformat()

            update_expression_parts = ["last_seen = :last_seen", "updated_at = :updated_at"]
            expression_values = {
                ":last_seen": now,
                ":updated_at": now,
            }
            expression_names = {}

            if status:
                update_expression_parts.append("#status = :status")
                expression_values[":status"] = status
                expression_names["#status"] = "status"

            update_expression = "SET " + ", ".join(update_expression_parts)

            key = {"pk": f"DEVICE#{device_id}", "sk": f"INFO#{device_id}"}
            await self.dynamo_repository.dynamo_client.update_item(
                key=key,
                update_expression=update_expression,
                expression_values=expression_values,
                expression_names=expression_names if expression_names else None,
            )

            if additional_data:
                updated_stats = device.stats.copy()
                stats_updated = False

                if "uptime_hours" in additional_data:
                    updated_stats["uptime_hours"] = additional_data["uptime_hours"]
                    stats_updated = True

                if "total_captures" in additional_data:
                    logger.warning(
                        f"Dispositivo {device_id} tentou atualizar total_captures via heartbeat. "
                        f"Ignorando (valor local: {additional_data['total_captures']}, "
                        f"valor servidor: {updated_stats.get('total_captures', 0)}). "
                        "total_captures é calculado pelo servidor baseado em notificações SNS."
                    )

                if stats_updated:
                    await self.dynamo_repository.update_device_stats(device_id, updated_stats)

            device = await self.dynamo_repository.get_device_by_id(device_id)

            logger.debug(f"Heartbeat processado: {device_id} - status atualizado para {status}")

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
            logger.exception(f"Erro ao processar heartbeat: {e}")
            raise

    async def get_device_by_id(self, device_id: str) -> Optional[Device]:
        try:
            return await get_device_by_id_cached(
                device_id=device_id, dynamo_repository=self.dynamo_repository, ttl_hash=get_current_minute_timestamp()
            )
        except Exception as e:
            logger.exception(f"Erro ao obter dispositivo: {e}")
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
                logger.warning(f"Dispositivo {device_id} não encontrado")
                return None

            device.update_config(config_updates)
            await self.dynamo_repository.save_device(device)

            logger.info(f"Configuração atualizada: {device_id}")
            return device.config
        except Exception as e:
            logger.exception(f"Erro ao atualizar configuração: {e}")
            raise

    async def update_device_statistics(self, device_id: str, processing_result: Dict[str, Any]) -> bool:
        try:
            device = await self.dynamo_repository.get_device_by_id(device_id)
            if not device:
                logger.warning(f"Dispositivo {device_id} não encontrado")
                return False

            success = processing_result.get("success", False)
            device.increment_capture_count(success=success)
            new_total = device.stats.get("total_captures", 0)

            if processing_result.get("processing_time_ms"):
                current_avg = device.stats.get("average_processing_time_ms", 0)
                if new_total > 0:
                    new_avg = ((current_avg * (new_total - 1)) + processing_result["processing_time_ms"]) / new_total
                    device.stats["average_processing_time_ms"] = int(new_avg)
                else:
                    device.stats["average_processing_time_ms"] = int(processing_result["processing_time_ms"])
            await self.dynamo_repository.save_device(device)
            logger.info(f"Estatísticas atualizadas: {device_id}")
            return True
        except Exception as e:
            logger.exception(f"Erro ao atualizar estatísticas: {e}")
            raise

    async def get_device_statistics(self) -> Dict[str, Any]:
        try:
            devices = await self.dynamo_repository.list_devices(limit=1000)

            total_devices = len(devices)
            status_counts = {}
            devices_by_location = {}

            for device in devices:
                status_counts[device.status] = status_counts.get(device.status, 0) + 1
                devices_by_location[device.location] = devices_by_location.get(device.location, 0) + 1

            recent_registrations = []
            sorted_devices = sorted(devices, key=lambda d: d.created_at, reverse=True)[:5]

            for device in sorted_devices:
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
                "online_devices": status_counts.get("online", 0),
                "offline_devices": status_counts.get("offline", 0),
                "maintenance_devices": status_counts.get("maintenance", 0),
                "error_devices": status_counts.get("error", 0),
                "devices_by_location": devices_by_location,
                "recent_registrations": recent_registrations,
            }
        except Exception as e:
            logger.exception(f"Erro ao obter estatísticas: {e}")
            raise

    async def update_global_config(self, global_config: Dict[str, Any]) -> Dict[str, Any]:
        try:
            devices = await self.dynamo_repository.get_devices_by_status("online", limit=1000)

            config_mapping = {
                "min_capture_interval": "capture_interval",
                "image_quality": "image_quality",
                "max_resolution": "image_resolution",
                "min_detection_confidence": "detection_confidence",
                "min_maturation_confidence": "maturation_confidence",
            }

            device_config_updates = {
                device_key: global_config[global_key]
                for global_key, device_key in config_mapping.items()
                if global_key in global_config
            }

            affected_devices = 0
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
            timeout_minutes = settings.HEARTBEAT_TIMEOUT_MINUTES
            offline_device_ids = await self.dynamo_repository.get_offline_devices_optimized(timeout_minutes)

            if offline_device_ids:
                await self.dynamo_repository.batch_update_device_status(offline_device_ids, "offline")
                logger.warning(f"Dispositivos offline: {len(offline_device_ids)}")

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
            logger.exception(f"Erro ao obter dispositivos por status: {e}")
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

            active_devices = [d for d in devices if d.stats and d.stats.get("total_captures", 0) > 0]
            active_devices.sort(key=lambda d: d.stats.get("total_captures", 0), reverse=True)
            top_active = active_devices[:5]

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
                    for d in top_active
                ],
                "average_captures": (
                    sum(d.stats.get("total_captures", 0) for d in devices) / len(devices) if devices else 0
                ),
            }
        except Exception as e:
            logger.exception(f"Erro ao obter análise da localização: {e}")
            raise
