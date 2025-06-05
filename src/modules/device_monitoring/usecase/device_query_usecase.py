import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.modules.device_monitoring.repo.device_repository import DeviceRepository
from src.shared.domain.entities.device import Device

logger = logging.getLogger(__name__)


class DeviceQueryUseCase:
    def __init__(self, device_repository: Optional[DeviceRepository] = None):
        self.device_repository = device_repository or DeviceRepository()

    async def get_device(self, device_id: str) -> Optional[Device]:
        try:
            return await self.device_repository.get_device(device_id)
        except Exception as e:
            logger.exception(f"Erro ao obter dispositivo: {e}")
            raise

    async def list_devices(
        self, status_filter: Optional[str] = None, location_filter: Optional[str] = None
    ) -> List[Device]:
        try:
            return await self.device_repository.list_devices(status_filter, location_filter)
        except Exception as e:
            logger.exception(f"Erro ao listar dispositivos: {e}")
            raise

    async def get_dashboard_data(self) -> Dict[str, Any]:
        try:
            devices = await self.list_devices()

            dashboard_calculator = DashboardDataCalculator()
            return dashboard_calculator.calculate(devices)

        except Exception as e:
            logger.exception(f"Erro ao obter dados do dashboard: {e}")
            return {}


class DashboardDataCalculator:
    def calculate(self, devices: List[Device]) -> Dict[str, Any]:
        status_counts = self._calculate_status_counts(devices)
        locations = self._calculate_locations(devices)
        capture_stats = self._calculate_capture_stats(devices)

        return {
            "total_devices": len(devices),
            **status_counts,
            "total_captures_today": capture_stats["today"],
            "total_captures_week": capture_stats["week"],
            "processing_queue": 0,
            "average_success_rate": capture_stats["success_rate"],
            "devices_by_location": locations,
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }

    def _calculate_status_counts(self, devices: List[Device]) -> Dict[str, int]:
        status_counts = {"online": 0, "offline": 0, "maintenance": 0, "pending": 0, "error": 0}

        for device in devices:
            device_status = device.status if device.status in status_counts else "error"
            status_counts[device_status] += 1

        return {
            "online_devices": status_counts["online"],
            "offline_devices": status_counts["offline"],
            "maintenance_devices": status_counts["maintenance"],
            "pending_devices": status_counts["pending"],
            "error_devices": status_counts["error"],
        }

    def _calculate_locations(self, devices: List[Device]) -> Dict[str, int]:
        locations = {}
        for device in devices:
            locations[device.location] = locations.get(device.location, 0) + 1
        return locations

    def _calculate_capture_stats(self, devices: List[Device]) -> Dict[str, Any]:
        today = datetime.now(timezone.utc).date()
        total_captures_today = 0
        total_successful = 0
        total_failed = 0

        for device in devices:
            if device.last_seen and device.last_seen.date() == today:
                total_captures_today += device.stats.get("total_captures", 0)

            total_successful += device.stats.get("successful_captures", 0)
            total_failed += device.stats.get("failed_captures", 0)

        success_rate = 0.0
        if (total_successful + total_failed) > 0:
            success_rate = (total_successful / (total_successful + total_failed)) * 100

        return {
            "today": total_captures_today,
            "week": sum(d.stats.get("total_captures", 0) for d in devices),
            "success_rate": round(success_rate, 2),
        }
