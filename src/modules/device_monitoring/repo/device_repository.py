import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from src.app.config import settings
from src.shared.domain.entities.device import Device
from src.shared.infra.external.dynamo.dynamo_client import DynamoClient

logger = logging.getLogger(__name__)


class DeviceRepository:
    """Repositório para gerenciamento de dispositivos no DynamoDB."""

    def __init__(self, dynamo_client: Optional[DynamoClient] = None):
        self.devices_table = settings.DYNAMODB_DEVICES_TABLE
        self.activities_table = settings.DYNAMODB_DEVICE_ACTIVITIES_TABLE

        self.devices_client = DynamoClient(table_name=self.devices_table)
        self.activities_client = DynamoClient(table_name=self.activities_table)

    async def save_device(self, device: Device) -> Dict[str, Any]:
        """Salva um dispositivo na tabela de dispositivos."""
        try:
            item = device.to_dict()
            logger.info(f"Salvando dispositivo {device.device_id} na tabela {self.devices_table}")
            return await self.devices_client.put_item(item)

        except Exception as e:
            logger.exception(f"Erro ao salvar dispositivo na tabela {self.devices_table}: {e}")
            raise

    async def get_device(self, device_id: str) -> Optional[Device]:
        """Recupera um dispositivo pelo ID."""
        try:
            key = {"pk": f"DEVICE#{device_id}", "sk": f"INFO#{device_id}"}
            item = await self.devices_client.get_item(key)

            if not item:
                logger.warning(f"Dispositivo não encontrado: {device_id}")
                return None

            return Device.from_dict(item)

        except Exception as e:
            logger.exception(f"Erro ao recuperar dispositivo da tabela {self.devices_table}: {e}")
            raise

    async def update_device(self, device: Device) -> Dict[str, Any]:
        """Atualiza um dispositivo na tabela de dispositivos."""
        try:
            device.updated_at = datetime.now(timezone.utc)
            item = device.to_dict()

            logger.info(f"Atualizando dispositivo {device.device_id} na tabela {self.devices_table}")
            return await self.devices_client.put_item(item)

        except Exception as e:
            logger.exception(f"Erro ao atualizar dispositivo na tabela {self.devices_table}: {e}")
            raise

    async def list_devices(
        self, status_filter: Optional[str] = None, location_filter: Optional[str] = None, limit: int = 100
    ) -> List[Device]:
        """Lista dispositivos com filtros opcionais."""
        try:
            scan_params = {
                "filter_expression": "begins_with(pk, :pk_prefix) AND entity_type = :entity_type",
                "expression_values": {":pk_prefix": "DEVICE#", ":entity_type": "DEVICE"},
                "limit": limit,
            }

            if status_filter:
                scan_params["filter_expression"] += " AND #status = :status"
                scan_params["expression_names"] = {"#status": "status"}
                scan_params["expression_values"][":status"] = status_filter

            if location_filter:
                scan_params["filter_expression"] += " AND contains(#location, :location)"
                if "expression_names" not in scan_params:
                    scan_params["expression_names"] = {}
                scan_params["expression_names"]["#location"] = "location"
                scan_params["expression_values"][":location"] = location_filter

            items = await self.devices_client.scan(**scan_params)

            devices = []
            for item in items:
                try:
                    device = Device.from_dict(item)
                    devices.append(device)
                except Exception as e:
                    logger.warning(f"Erro ao converter item do DynamoDB para Device: {e}")
                    continue

            logger.info(f"Recuperados {len(devices)} dispositivos da tabela {self.devices_table}")
            return devices

        except Exception as e:
            logger.exception(f"Erro ao listar dispositivos da tabela {self.devices_table}: {e}")
            raise

    async def delete_device(self, device_id: str) -> bool:
        """Remove um dispositivo da tabela de dispositivos."""
        try:
            key = {"pk": f"DEVICE#{device_id}", "sk": f"INFO#{device_id}"}

            existing = await self.devices_client.get_item(key)
            if not existing:
                logger.warning(f"Tentativa de deletar dispositivo inexistente: {device_id}")
                return False

            await self.devices_client.delete_item(key)
            logger.info(f"Dispositivo {device_id} removido da tabela {self.devices_table}")
            return True

        except Exception as e:
            logger.exception(f"Erro ao deletar dispositivo da tabela {self.devices_table}: {e}")
            return False

    async def get_devices_by_status(self, status: str) -> List[Device]:
        """Recupera dispositivos por status usando índice."""
        try:
            items = await self.devices_client.query_items(key_name="status", key_value=status, index_name="StatusIndex")

            devices = []
            for item in items:
                try:
                    devices.append(Device.from_dict(item))
                except Exception as e:
                    logger.warning(f"Erro ao converter item para Device: {e}")

            return devices

        except Exception as e:
            logger.exception(f"Erro ao buscar dispositivos por status: {e}")
            raise

    async def get_devices_by_location(self, location: str) -> List[Device]:
        """Recupera dispositivos por localização usando índice."""
        try:
            items = await self.devices_client.query_items(
                key_name="location", key_value=location, index_name="LocationIndex"
            )

            devices = []
            for item in items:
                try:
                    devices.append(Device.from_dict(item))
                except Exception as e:
                    logger.warning(f"Erro ao converter item para Device: {e}")

            return devices

        except Exception as e:
            logger.exception(f"Erro ao buscar dispositivos por localização: {e}")
            raise

    async def get_offline_devices(self, timeout_minutes: int = 5) -> List[Device]:
        """Recupera dispositivos que estão offline (sem heartbeat recente)."""
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=timeout_minutes)
            cutoff_iso = cutoff_time.isoformat()

            filter_expr = (
                "begins_with(pk, :pk_prefix) AND entity_type = :entity_type AND "
                "(attribute_not_exists(last_seen) OR last_seen < :cutoff_time)"
            )

            items = await self.devices_client.scan(
                filter_expression=filter_expr,
                expression_values={":pk_prefix": "DEVICE#", ":entity_type": "DEVICE", ":cutoff_time": cutoff_iso},
            )

            devices = []
            for item in items:
                try:
                    device = Device.from_dict(item)
                    if not device.is_online(timeout_minutes):
                        devices.append(device)
                except Exception as e:
                    logger.warning(f"Erro ao converter item para Device: {e}")

            return devices

        except Exception as e:
            logger.exception(f"Erro ao buscar dispositivos offline: {e}")
            raise

    async def save_device_activity(self, device_id: str, activity_type: str, details: Dict[str, Any]) -> str:
        """Salva uma atividade do dispositivo na tabela de atividades."""
        try:
            activity_id = f"activity-{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}-{device_id[:8]}"
            timestamp = datetime.now(timezone.utc).isoformat()

            activity_item = {
                "device_id": device_id,
                "timestamp": timestamp,
                "activity_id": activity_id,
                "activity_type": activity_type,
                "details": details,
                "ttl": int((datetime.now(timezone.utc) + timedelta(days=30)).timestamp()),
            }

            await self.activities_client.put_item(activity_item)
            logger.info(f"Atividade {activity_id} salva para dispositivo {device_id} na tabela {self.activities_table}")
            return activity_id

        except Exception as e:
            logger.exception(f"Erro ao salvar atividade na tabela {self.activities_table}: {e}")
            raise

    async def get_device_activities(self, device_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Recupera atividades de um dispositivo da tabela de atividades."""
        try:
            items = await self.activities_client.query_items(
                key_name="device_id", key_value=device_id, limit=limit, scan_index_forward=False
            )

            activities = []
            for item in items:
                activities.append(
                    {
                        "activity_id": item.get("activity_id"),
                        "activity_type": item.get("activity_type"),
                        "details": item.get("details", {}),
                        "timestamp": item.get("timestamp"),
                    }
                )

            return activities

        except Exception as e:
            logger.exception(f"Erro ao buscar atividades da tabela {self.activities_table}: {e}")
            raise

    async def get_device_statistics(self, device_id: str, days: int = 7) -> Optional[Dict[str, Any]]:
        """Recupera estatísticas de um dispositivo."""
        try:
            device = await self.get_device(device_id)
            if not device:
                return None

            activities = await self.get_device_activities(device_id, limit=1000)

            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            recent_activities = [a for a in activities if datetime.fromisoformat(a["timestamp"]) > cutoff_date]

            capture_activities = [a for a in recent_activities if "capture" in a["activity_type"]]

            stats = {
                "device_id": device_id,
                "period_days": days,
                "total_captures": len(capture_activities),
                "successful_captures": device.stats.get("successful_captures", 0),
                "failed_captures": device.stats.get("failed_captures", 0),
                "success_rate": 0.0,
                "uptime_percentage": 0.0,
                "last_activity": device.last_seen.isoformat() if device.last_seen else None,
                "status": device.status,
                "recent_activities_count": len(recent_activities),
            }

            total = stats["successful_captures"] + stats["failed_captures"]
            if total > 0:
                stats["success_rate"] = (stats["successful_captures"] / total) * 100

            return stats

        except Exception as e:
            logger.exception(f"Erro ao calcular estatísticas do dispositivo: {e}")
            return None

    async def update_device_stats(self, device_id: str, stat_type: str, value: Any = 1) -> bool:
        """Atualiza estatísticas específicas de um dispositivo."""
        try:
            device = await self.get_device(device_id)
            if not device:
                return False

            if stat_type == "capture_success":
                device.stats["successful_captures"] += value
                device.stats["total_captures"] += value
            elif stat_type == "capture_fail":
                device.stats["failed_captures"] += value
                device.stats["total_captures"] += value
            elif stat_type == "capture_processed":
                device.stats["total_captures"] += value
            elif stat_type == "capture_uploaded":
                device.stats["total_captures"] += value
            elif stat_type == "uptime":
                device.stats["uptime_hours"] = value

            await self.update_device(device)
            return True

        except Exception as e:
            logger.exception(f"Erro ao atualizar estatísticas do dispositivo: {e}")
            return False

    async def cleanup_old_activities(self, days_old: int = 30) -> int:
        """Remove atividades antigas da tabela (backup do TTL)."""
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_old)
            cutoff_iso = cutoff_date.isoformat()

            items = await self.activities_client.scan(
                filter_expression="timestamp < :cutoff_date", expression_values={":cutoff_date": cutoff_iso}
            )

            deleted_count = 0
            for item in items:
                try:
                    key = {"device_id": item["device_id"], "timestamp": item["timestamp"]}
                    await self.activities_client.delete_item(key)
                    deleted_count += 1
                except Exception as e:
                    logger.warning(f"Erro ao deletar atividade antiga: {e}")

            logger.info(f"Removidas {deleted_count} atividades antigas da tabela {self.activities_table}")
            return deleted_count

        except Exception as e:
            logger.exception(f"Erro na limpeza de atividades antigas: {e}")
            return 0
