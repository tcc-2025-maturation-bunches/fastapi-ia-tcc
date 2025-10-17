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
                    "device_id": device.device_id,
                    "status": device.status,
                    "location": device.location,
                    "created_at": device.created_at.isoformat(),
                    "updated_at": device.updated_at.isoformat(),
                }
            )
            await self.dynamo_client.put_item(item)
            logger.debug(f"Dispositivo {device.device_id} salvo")
            return device
        except Exception as e:
            logger.exception(f"Erro ao salvar dispositivo {device.device_id}: {e}")
            raise

    async def get_device_by_id(self, device_id: str) -> Optional[Device]:
        try:
            key = {"pk": f"DEVICE#{device_id}", "sk": f"INFO#{device_id}"}
            item = await self.dynamo_client.get_item(key)

            if not item:
                logger.debug(f"Dispositivo {device_id} não encontrado")
                return None

            return Device.from_dict(item)
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
            if status_filter and location_filter:
                devices = await self._query_by_status_and_location(status_filter, location_filter, limit)
            elif status_filter:
                devices = await self.get_devices_by_status(status_filter, limit)
            elif location_filter:
                devices = await self.get_devices_by_location(location_filter, limit)
            else:
                query_result = await self.dynamo_client.query_with_pagination(
                    key_name="entity_type",
                    key_value="DEVICE",
                    index_name="EntityTypeIndex",
                    limit=limit,
                    scan_index_forward=False,
                )
                devices = [Device.from_dict(item) for item in query_result.get("items", [])]

            logger.debug(f"Listagem retornou {len(devices)} dispositivos")
            return devices
        except Exception as e:
            logger.exception(f"Erro ao listar dispositivos: {e}")
            raise

    async def _query_by_status_and_location(self, status: str, location: str, limit: int) -> List[Device]:
        devices_by_location = await self.get_devices_by_location(location, limit * 2)
        filtered = [d for d in devices_by_location if d.status == status]
        return filtered[:limit]

    async def delete_device(self, device_id: str) -> bool:
        try:
            key = {"pk": f"DEVICE#{device_id}", "sk": f"INFO#{device_id}"}
            success = await self.dynamo_client.delete_item(key)
            if success:
                logger.info(f"Dispositivo {device_id} removido")
            return success
        except Exception as e:
            logger.exception(f"Erro ao remover dispositivo {device_id}: {e}")
            return False

    async def get_devices_by_status(self, status: str, limit: int = 100) -> List[Device]:
        try:
            query_result = await self.dynamo_client.query_with_pagination(
                key_name="status",
                key_value=status,
                index_name="DeviceStatusIndex",
                limit=limit,
                scan_index_forward=False,
            )

            devices = [Device.from_dict(item) for item in query_result.get("items", [])]
            logger.debug(f"Encontrados {len(devices)} dispositivos com status {status}")
            return devices
        except Exception as e:
            logger.exception(f"Erro ao obter dispositivos por status: {e}")
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

            devices = [Device.from_dict(item) for item in query_result.get("items", [])]
            logger.debug(f"Encontrados {len(devices)} dispositivos na localização {location}")
            return devices
        except Exception as e:
            logger.exception(f"Erro ao obter dispositivos por localização: {e}")
            raise

    async def update_device_status(self, device_id: str, status: str) -> bool:
        try:
            key = {"pk": f"DEVICE#{device_id}", "sk": f"INFO#{device_id}"}
            now = datetime.now(timezone.utc).isoformat()

            update_expression = "SET #status = :status, updated_at = :updated_at"
            expression_values = {
                ":status": status,
                ":updated_at": now,
            }
            expression_names = {"#status": "status"}

            await self.dynamo_client.update_item(
                key=key,
                update_expression=update_expression,
                expression_values=expression_values,
                expression_names=expression_names,
            )

            logger.debug(f"Status do dispositivo {device_id} atualizado para {status}")
            return True
        except Exception as e:
            logger.exception(f"Erro ao atualizar status: {e}")
            return False

    async def update_device_config(self, device_id: str, config: dict) -> bool:
        try:
            key = {"pk": f"DEVICE#{device_id}", "sk": f"INFO#{device_id}"}
            now = datetime.now(timezone.utc).isoformat()

            update_expression = "SET config = :config, updated_at = :updated_at"
            expression_values = {":config": config, ":updated_at": now}

            await self.dynamo_client.update_item(
                key=key,
                update_expression=update_expression,
                expression_values=expression_values,
            )

            logger.debug(f"Configuração do dispositivo {device_id} atualizada")
            return True
        except Exception as e:
            logger.exception(f"Erro ao atualizar configuração: {e}")
            return False

    async def update_device_stats(self, device_id: str, stats: dict) -> bool:
        try:
            key = {"pk": f"DEVICE#{device_id}", "sk": f"INFO#{device_id}"}
            now = datetime.now(timezone.utc).isoformat()

            update_expression = "SET stats = :stats, updated_at = :updated_at, last_seen = :last_seen"
            expression_values = {":stats": stats, ":updated_at": now, ":last_seen": now}

            await self.dynamo_client.update_item(
                key=key,
                update_expression=update_expression,
                expression_values=expression_values,
            )

            logger.debug(f"Estatísticas do dispositivo {device_id} atualizadas")
            return True
        except Exception as e:
            logger.exception(f"Erro ao atualizar estatísticas: {e}")
            return False

    async def get_offline_devices_optimized(self, timeout_minutes: int = 5) -> List[str]:
        try:
            cutoff_timestamp = datetime.now(timezone.utc).timestamp() - (timeout_minutes * 60)
            cutoff_iso = datetime.fromtimestamp(cutoff_timestamp, tz=timezone.utc).isoformat()

            try:
                query_result = await self.dynamo_client.query_with_pagination(
                    key_name="status",
                    key_value="online",
                    index_name="DeviceStatusIndex",
                    limit=1000,
                    scan_index_forward=False,
                )
            except Exception as e:
                logger.warning(f"DeviceStatusIndex falhou, usando EntityTypeIndex: {e}")
                query_result = await self.dynamo_client.query_with_pagination(
                    key_name="entity_type",
                    key_value="DEVICE",
                    index_name="EntityTypeIndex",
                    limit=1000,
                    filter_expression="#status = :status",
                    expression_values={":status": "online"},
                    expression_names={"#status": "status"},
                    scan_index_forward=False,
                )

            offline_device_ids = []
            for item in query_result.get("items", []):
                last_seen = item.get("last_seen")
                if last_seen and last_seen < cutoff_iso:
                    offline_device_ids.append(item["device_id"])

            logger.debug(f"Encontrados {len(offline_device_ids)} dispositivos offline")
            return offline_device_ids
        except Exception as e:
            logger.exception(f"Erro ao obter dispositivos offline: {e}")
            raise

    async def get_offline_devices(self, timeout_minutes: int = 5) -> List[Device]:
        try:
            offline_ids = await self.get_offline_devices_optimized(timeout_minutes)

            if not offline_ids:
                return []

            devices = []
            for device_id in offline_ids:
                device = await self.get_device_by_id(device_id)
                if device:
                    devices.append(device)

            return devices
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
            logger.exception(f"Erro ao obter estatísticas da localização: {e}")
            raise

    async def update_device_last_seen(self, device_id: str) -> bool:
        try:
            key = {"pk": f"DEVICE#{device_id}", "sk": f"INFO#{device_id}"}
            now = datetime.now(timezone.utc).isoformat()

            update_expression = "SET last_seen = :last_seen, updated_at = :updated_at"
            expression_values = {":last_seen": now, ":updated_at": now}

            await self.dynamo_client.update_item(
                key=key,
                update_expression=update_expression,
                expression_values=expression_values,
            )

            logger.debug(f"Last seen do dispositivo {device_id} atualizado")
            return True
        except Exception as e:
            logger.exception(f"Erro ao atualizar last seen: {e}")
            return False

    async def get_recently_active_devices(self, limit: int = 50) -> List[Device]:
        try:
            query_result = await self.dynamo_client.query_with_pagination(
                key_name="entity_type",
                key_value="DEVICE",
                index_name="EntityTypeIndex",
                limit=limit * 2,
                scan_index_forward=False,
            )

            devices = []
            for item in query_result.get("items", []):
                try:
                    device = Device.from_dict(item)
                    devices.append(device)
                except Exception as e:
                    logger.warning(f"Erro ao converter item: {e}")
                    continue

            devices.sort(key=lambda d: d.last_seen or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
            result = devices[:limit]

            logger.debug(f"Encontrados {len(result)} dispositivos recentes")
            return result
        except Exception as e:
            logger.exception(f"Erro ao obter dispositivos recentes: {e}")
            raise

    async def batch_update_device_status(self, device_ids: List[str], status: str) -> int:
        updated_count = 0
        for device_id in device_ids:
            success = await self.update_device_status(device_id, status)
            if success:
                updated_count += 1

        logger.info(f"Atualização em lote: {updated_count}/{len(device_ids)} dispositivos")
        return updated_count
