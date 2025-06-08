import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from src.modules.device_monitoring.repo.device_repository import DeviceRepository
from src.shared.domain.entities.device import Device

logger = logging.getLogger(__name__)


class DeviceRegistrationUseCase:
    def __init__(self, device_repository: Optional[DeviceRepository] = None):
        self.device_repository = device_repository or DeviceRepository()

    async def register_device(
        self, device_id: str, device_name: str, location: str, capabilities: Dict[str, Any]
    ) -> Device:
        try:
            existing_device = await self.device_repository.get_device(device_id)
            if existing_device:
                return await self._update_existing_device(existing_device, device_name, location, capabilities)

            return await self._create_new_device(device_id, device_name, location, capabilities)

        except Exception as e:
            logger.exception(f"Erro ao registrar dispositivo: {e}")
            raise

    async def _update_existing_device(
        self, device: Device, device_name: str, location: str, capabilities: Dict[str, Any]
    ) -> Device:
        device.device_name = device_name
        device.location = location
        device.capabilities = capabilities
        device.status = "online"
        device.last_seen = datetime.now(timezone.utc)
        device.updated_at = datetime.now(timezone.utc)

        await self.device_repository.update_device(device)
        await self.device_repository.save_device_activity(
            device.device_id, "device_updated", {"name": device_name, "location": location}
        )

        logger.info(f"Dispositivo atualizado: {device.device_id}")
        return device

    async def _create_new_device(
        self, device_id: str, device_name: str, location: str, capabilities: Dict[str, Any]
    ) -> Device:
        device = Device(
            device_id=device_id,
            device_name=device_name,
            location=location,
            capabilities=capabilities,
            status="online",
        )

        await self.device_repository.save_device(device)
        await self.device_repository.save_device_activity(
            device_id, "device_registered", {"name": device_name, "location": location}
        )

        logger.info(f"Novo dispositivo registrado: {device_id}")
        return device

    async def unregister_device(self, device_id: str) -> bool:
        try:
            device = await self.device_repository.get_device(device_id)
            if not device:
                return False

            await self.device_repository.save_device_activity(
                device_id, "device_unregistered", {"name": device.device_name, "location": device.location}
            )

            success = await self.device_repository.delete_device(device_id)
            if success:
                logger.info(f"Dispositivo {device_id} removido do sistema")

            return success

        except Exception as e:
            logger.exception(f"Erro ao remover dispositivo: {e}")
            return False
