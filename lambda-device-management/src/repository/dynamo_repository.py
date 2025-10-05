import logging
from datetime import datetime, timezone
from typing import List, Optional

from fruit_detection_shared.domain.entities import Device
from fruit_detection_shared.infra.external import DynamoClient

from src.app.config import settings

logger = logging.getLogger(__name__)


class DynamoRepository:
    def __init__(self, dynamo_client: DynamoClient = None):
        self.dynamo_client = dynamo_client or DynamoClient(table_name=settings.DYNAMODB_TABLE_NAME)

    async def save_device(self, device: Device) -> Device:
        try:
            item = device.to_dict()
            item.update(
                {
                    "entity_type": "DEVICE",
                    "createdAt": device.created_at.isoformat(),
                    "updatedAt": device.updated_at.isoformat(),
                }
            )
            await self.dynamo_client.put_item(item)
            logger.debug(f"Dispositivo {device.device_id} salvo no DynamoDB")
            return device
        except Exception as e:
            logger.exception(f"Erro ao salvar dispositivo {device.device_id}: {e}")
            raise

    async def get_device_by_id(self, device_id: str) -> Optional[Device]:
        try:
            query_result = await self.dynamo_client.query_with_pagination(
                key_name="pk", key_value=f"DEVICE#{device_id}", limit=1
            )

            items = query_result.get("items", [])
            if not items:
                logger.debug(f"Dispositivo {device_id} não encontrado")
                return None

            return Device.from_dict(items[0])

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
            query_result = await self.dynamo_client.query_with_pagination(
                key_name="entity_type",
                key_value="DEVICE",
                index_name="EntityTypeIndex",
                limit=limit,
                scan_index_forward=False,
            )

            devices = []
            for item in query_result.get("items", []):
                try:
                    device = Device.from_dict(item)

                    if status_filter and device.status != status_filter:
                        continue

                    if location_filter and device.location != location_filter:
                        continue

                    devices.append(device)

                except Exception as e:
                    logger.warning(f"Erro ao converter item para Device: {e}")
                    continue

            logger.debug(f"Listagem retornou {len(devices)} dispositivos")
            return devices

        except Exception as e:
            logger.exception(f"Erro ao listar dispositivos: {e}")
            raise

    async def delete_device(self, device_id: str) -> bool:
        try:
            device = await self.get_device_by_id(device_id)
            if not device:
                return False

            last_seen_str = (
                device.last_seen.strftime("%Y-%m-%d#%H:%M:%S") if device.last_seen else "1970-01-01#00:00:00"
            )
            sk = f"STATUS#{device.status}#LASTSEEN#{last_seen_str}"
            key = {"pk": f"DEVICE#{device_id}", "sk": sk}
            success = await self.dynamo_client.delete_item(key)

            if success:
                logger.info(f"Dispositivo {device_id} removido do DynamoDB")

            return success

        except Exception as e:
            logger.exception(f"Erro ao remover dispositivo {device_id}: {e}")
            return False

    async def get_devices_by_status(self, status: str, limit: int = 100) -> List[Device]:
        try:
            query_result = await self.dynamo_client.query_with_pagination(
                key_name="entity_type",
                key_value="DEVICE",
                index_name="EntityTypeIndex",
                limit=limit,
                filter_expression="begins_with(sk, :sk_prefix)",
                expression_values={":sk_prefix": f"STATUS#{status}#"},
                scan_index_forward=False,
            )

            devices = []
            for item in query_result.get("items", []):
                try:
                    device = Device.from_dict(item)
                    devices.append(device)
                except Exception as e:
                    logger.warning(f"Erro ao converter item para Device: {e}")
                    continue

            logger.debug(f"Encontrados {len(devices)} dispositivos com status {status}")
            return devices

        except Exception as e:
            logger.exception(f"Erro ao obter dispositivos por status {status}: {e}")
            raise

        except Exception as e:
            logger.exception(f"Erro ao obter dispositivos por status {status}: {e}")
            raise

    async def get_devices_by_location(self, location: str, limit: int = 100) -> List[Device]:
        try:
            query_result = await self.dynamo_client.query_with_pagination(
                key_name="location",
                key_value=location,
                index_name="DeviceLocationIndex",
                limit=limit,
                scan_index_forward=False,
            )

            devices = []
            for item in query_result.get("items", []):
                try:
                    device = Device.from_dict(item)
                    devices.append(device)
                except Exception as e:
                    logger.warning(f"Erro ao converter item para Device: {e}")
                    continue

            logger.debug(f"Encontrados {len(devices)} dispositivos na localização {location}")
            return devices

        except Exception as e:
            logger.exception(f"Erro ao obter dispositivos por localização {location}: {e}")
            raise

    async def update_device_status(self, device_id: str, status: str) -> bool:
        try:
            device = await self.get_device_by_id(device_id)
            if not device:
                logger.warning(f"Dispositivo {device_id} não encontrado para atualização")
                return False

            last_seen_str = (
                device.last_seen.strftime("%Y-%m-%d#%H:%M:%S") if device.last_seen else "1970-01-01#00:00:00"
            )
            old_sk = f"STATUS#{device.status}#LASTSEEN#{last_seen_str}"
            old_key = {"pk": f"DEVICE#{device_id}", "sk": old_sk}

            device.status = status
            device.last_seen = datetime.now(timezone.utc)
            device.updated_at = datetime.now(timezone.utc)

            await self.dynamo_client.delete_item(old_key)
            await self.save_device(device)

            logger.debug(f"Status do dispositivo {device_id} atualizado para {status}")
            return True

        except Exception as e:
            logger.exception(f"Erro ao atualizar status do dispositivo {device_id}: {e}")
            return False

    async def update_device_config(self, device_id: str, config: dict) -> bool:
        try:
            key = {"pk": f"DEVICE#{device_id}", "sk": f"INFO#{device_id}"}
            now = datetime.now(timezone.utc).isoformat()

            update_expression = "SET config = :config, updatedAt = :updated_at"
            expression_values = {
                ":config": config,
                ":updated_at": now,
            }

            await self.dynamo_client.update_item(
                key=key,
                update_expression=update_expression,
                expression_values=expression_values,
            )

            logger.debug(f"Configuração do dispositivo {device_id} atualizada")
            return True

        except Exception as e:
            logger.exception(f"Erro ao atualizar configuração do dispositivo {device_id}: {e}")
            return False

    async def update_device_stats(self, device_id: str, stats: dict) -> bool:
        try:
            key = {"pk": f"DEVICE#{device_id}", "sk": f"INFO#{device_id}"}
            now = datetime.now(timezone.utc).isoformat()

            update_expression = "SET stats = :stats, updatedAt = :updated_at, last_seen = :last_seen"
            expression_values = {
                ":stats": stats,
                ":updated_at": now,
                ":last_seen": now,
            }

            await self.dynamo_client.update_item(
                key=key,
                update_expression=update_expression,
                expression_values=expression_values,
            )

            logger.debug(f"Estatísticas do dispositivo {device_id} atualizadas")
            return True

        except Exception as e:
            logger.exception(f"Erro ao atualizar estatísticas do dispositivo {device_id}: {e}")
            return False

    async def get_offline_devices(self, timeout_minutes: int = 5) -> List[Device]:
        try:
            cutoff_time = datetime.now(timezone.utc).timestamp() - (timeout_minutes * 60)

            online_devices = await self.get_devices_by_status("online")

            offline_devices = []
            for device in online_devices:
                if device.last_seen:
                    last_seen = datetime.fromisoformat(device.last_seen.replace("Z", "+00:00"))
                    if last_seen.timestamp() < cutoff_time:
                        offline_devices.append(device)

            logger.debug(f"Encontrados {len(offline_devices)} dispositivos offline")
            return offline_devices

        except Exception as e:
            logger.exception(f"Erro ao obter dispositivos offline: {e}")
            raise

    async def get_location_statistics(self, location: str) -> dict:
        try:
            devices = await self.get_devices_by_location(location)

            total_devices = len(devices)
            online_devices = sum(1 for d in devices if d.status == "online")

            total_captures = sum(d.stats.get("total_captures", 0) if d.stats else 0 for d in devices)

            return {
                "location": location,
                "total_devices": total_devices,
                "online_devices": online_devices,
                "offline_devices": total_devices - online_devices,
                "total_captures": total_captures,
                "average_captures_per_device": total_captures / total_devices if total_devices > 0 else 0,
            }

        except Exception as e:
            logger.exception(f"Erro ao obter estatísticas da localização {location}: {e}")
            raise

    async def update_device_last_seen(self, device_id: str) -> bool:
        try:
            key = {"pk": f"DEVICE#{device_id}", "sk": f"INFO#{device_id}"}
            now = datetime.now(timezone.utc).isoformat()

            update_expression = "SET last_seen = :last_seen, updatedAt = :updated_at"
            expression_values = {
                ":last_seen": now,
                ":updated_at": now,
            }

            await self.dynamo_client.update_item(
                key=key,
                update_expression=update_expression,
                expression_values=expression_values,
            )

            logger.debug(f"Last seen do dispositivo {device_id} atualizado")
            return True

        except Exception as e:
            logger.exception(f"Erro ao atualizar last seen do dispositivo {device_id}: {e}")
            return False

    async def get_recently_active_devices(self, limit: int = 50) -> List[Device]:
        try:
            query_result = await self.dynamo_client.query_with_pagination(
                key_name="entity_type",
                key_value="DEVICE",
                index_name="EntityTypeIndex",
                limit=limit,
                scan_index_forward=False,
            )

            devices = []
            for item in query_result.get("items", []):
                try:
                    device = Device.from_dict(item)
                    devices.append(device)
                except Exception as e:
                    logger.warning(f"Erro ao converter item para Device: {e}")
                    continue

            devices.sort(key=lambda d: d.last_seen or datetime.min.replace(tzinfo=timezone.utc), reverse=True)

            logger.debug(f"Encontrados {len(devices)} dispositivos ordenados por último acesso")
            return devices

        except Exception as e:
            logger.exception(f"Erro ao obter dispositivos recentes: {e}")
            raise
