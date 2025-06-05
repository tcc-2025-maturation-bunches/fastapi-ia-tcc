import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.modules.device_monitoring.repo.device_repository import DeviceRepository
from src.modules.device_monitoring.services.device_activity_service import DeviceActivityService
from src.modules.device_monitoring.services.device_stats_service import DeviceStatsService
from src.shared.domain.entities.device import Device

logger = logging.getLogger(__name__)


class DeviceMonitoringUseCase:
    def __init__(
        self,
        device_repository: Optional[DeviceRepository] = None,
        stats_service: Optional[DeviceStatsService] = None,
        activity_service: Optional[DeviceActivityService] = None,
    ):
        self.device_repository = device_repository or DeviceRepository()
        self.stats_service = stats_service or DeviceStatsService()
        self.activity_service = activity_service or DeviceActivityService(self.device_repository)

    async def update_device_heartbeat(
        self,
        device_id: str,
        status: str,
        last_seen: Optional[datetime] = None,
        additional_data: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Atualiza o heartbeat de um dispositivo"""
        try:
            device = await self.device_repository.get_device(device_id)
            if not device:
                logger.warning(f"Dispositivo {device_id} não encontrado para heartbeat")
                return False

            old_status = device.status

            device.status = status
            device.last_seen = last_seen or datetime.now(timezone.utc)
            device.updated_at = datetime.now(timezone.utc)

            if additional_data:
                self.stats_service.update_device_stats(device, additional_data)

            await self.device_repository.update_device(device)

            if old_status != status:
                await self.activity_service.log_status_change(device_id, old_status, status)

            logger.debug(f"Heartbeat atualizado para dispositivo {device_id}: {status}")
            return True

        except Exception as e:
            logger.exception(f"Erro ao atualizar heartbeat do dispositivo {device_id}: {e}")
            return False

    async def update_device_status(self, device_id: str, status: str, last_seen: Optional[datetime] = None) -> bool:
        """Atualiza apenas o status de um dispositivo"""
        try:
            device = await self.device_repository.get_device(device_id)
            if not device:
                logger.warning(f"Dispositivo {device_id} não encontrado para atualização de status")
                return False

            old_status = device.status
            device.status = status
            device.last_seen = last_seen or datetime.now(timezone.utc)
            device.updated_at = datetime.now(timezone.utc)

            await self.device_repository.update_device(device)
            await self.activity_service.log_status_change(device_id, old_status, status)

            logger.info(f"Status do dispositivo {device_id} alterado: {old_status} -> {status}")
            return True

        except Exception as e:
            logger.exception(f"Erro ao atualizar status do dispositivo {device_id}: {e}")
            return False

    async def get_offline_devices(self, timeout_minutes: int = 5) -> List[Device]:
        """Busca dispositivos que estão offline há mais tempo que o especificado"""
        try:
            return await self.device_repository.get_offline_devices(timeout_minutes)
        except Exception as e:
            logger.exception(f"Erro ao buscar dispositivos offline: {e}")
            return []

    async def check_and_update_offline_devices(self, timeout_minutes: int = 5) -> int:
        """Verifica e marca dispositivos como offline automaticamente"""
        try:
            offline_devices = await self.get_offline_devices(timeout_minutes)
            updated_count = 0

            for device in offline_devices:
                if device.status != "offline":
                    success = await self.update_device_status(device.device_id, "offline")
                    if success:
                        updated_count += 1

            if updated_count > 0:
                logger.info(f"Marcados {updated_count} dispositivos como offline automaticamente")

            return updated_count

        except Exception as e:
            logger.exception(f"Erro ao verificar dispositivos offline: {e}")
            return 0

    async def bulk_update_device_status(self, device_ids: List[str], status: str) -> Dict[str, bool]:
        """Atualiza o status de múltiplos dispositivos"""
        results = {}

        for device_id in device_ids:
            try:
                success = await self.update_device_status(device_id, status)
                results[device_id] = success
            except Exception as e:
                logger.exception(f"Erro ao atualizar status do dispositivo {device_id}: {e}")
                results[device_id] = False

        successful_updates = sum(results.values())
        logger.info(
            f"Atualização em lote: {successful_updates}/{len(device_ids)} dispositivos atualizados para '{status}'"
        )

        return results
