from typing import Any, Dict

from src.shared.domain.entities.device import Device


class DeviceStatsService:
    """Serviço responsável por gerenciar estatísticas dos dispositivos"""

    def update_device_stats(self, device: Device, additional_data: Dict[str, Any]):
        """Atualiza as estatísticas do dispositivo com dados adicionais"""
        if "capture_count" in additional_data:
            device.stats["total_captures"] = additional_data["capture_count"]

        if "uptime_hours" in additional_data:
            device.stats["uptime_hours"] = additional_data["uptime_hours"]

        if "successful_captures" in additional_data:
            device.stats["successful_captures"] = additional_data["successful_captures"]

        if "failed_captures" in additional_data:
            device.stats["failed_captures"] = additional_data["failed_captures"]

        if "memory_usage" in additional_data:
            device.stats["memory_usage"] = additional_data["memory_usage"]

        if "cpu_usage" in additional_data:
            device.stats["cpu_usage"] = additional_data["cpu_usage"]

        if "disk_usage" in additional_data:
            device.stats["disk_usage"] = additional_data["disk_usage"]

    def calculate_success_rate(self, device: Device) -> float:
        """Calcula a taxa de sucesso das capturas"""
        successful = device.stats.get("successful_captures", 0)
        failed = device.stats.get("failed_captures", 0)
        total = successful + failed

        if total == 0:
            return 0.0

        return (successful / total) * 100

    def get_device_health_score(self, device: Device) -> float:
        """Calcula um score de saúde do dispositivo (0-100)"""
        success_rate = self.calculate_success_rate(device)
        uptime_hours = device.stats.get("uptime_hours", 0)

        success_score = success_rate * 0.7

        uptime_score = min(uptime_hours / 24, 1.0) * 30

        return min(success_score + uptime_score, 100.0)
