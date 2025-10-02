import logging
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
            await self.dynamo_client.put_item(item)
            logger.debug(f"Dispositivo {device.device_id} salvo no DynamoDB")
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
            key = {"pk": f"DEVICE#{device_id}", "sk": f"INFO#{device_id}"}
            success = await self.dynamo_client.delete_item(key)

            if success:
                logger.info(f"Dispositivo {device_id} removido do DynamoDB")

            return success

        except Exception as e:
            logger.exception(f"Erro ao remover dispositivo {device_id}: {e}")
            return False

    async def get_devices_by_status(self, status: str, limit: int = 100) -> List[Device]:
        try:
            devices = await self.list_devices(status_filter=status, limit=limit)
            return devices

        except Exception as e:
            logger.exception(f"Erro ao obter dispositivos por status {status}: {e}")
            raise

    async def get_devices_by_location(self, location: str, limit: int = 100) -> List[Device]:
        try:
            devices = await self.list_devices(location_filter=location, limit=limit)
            return devices

        except Exception as e:
            logger.exception(f"Erro ao obter dispositivos por localização {location}: {e}")
            raise

    async def update_device_status(self, device_id: str, status: str) -> bool:
        try:
            key = {"pk": f"DEVICE#{device_id}", "sk": f"INFO#{device_id}"}

            update_expression = "SET #status = :status, updatedAt = :updated_at"
            expression_values = {
                ":status": status,
                ":updated_at": Device().updated_at.isoformat(),
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
            logger.exception(f"Erro ao atualizar status do dispositivo {device_id}: {e}")
            return False

    async def update_device_config(self, device_id: str, config: dict) -> bool:
        try:
            key = {"pk": f"DEVICE#{device_id}", "sk": f"INFO#{device_id}"}

            update_expression = "SET config = :config, updatedAt = :updated_at"
            expression_values = {
                ":config": config,
                ":updated_at": Device().updated_at.isoformat(),
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

            update_expression = "SET stats = :stats, updatedAt = :updated_at"
            expression_values = {
                ":stats": stats,
                ":updated_at": Device().updated_at.isoformat(),
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
