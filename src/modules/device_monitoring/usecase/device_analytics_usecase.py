import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from src.modules.device_monitoring.repo.device_repository import DeviceRepository
from src.modules.device_monitoring.services.device_stats_service import DeviceStatsService
from src.shared.domain.entities.device import Device

logger = logging.getLogger(__name__)


class DeviceAnalyticsUseCase:
    def __init__(
        self,
        device_repository: Optional[DeviceRepository] = None,
        stats_service: Optional[DeviceStatsService] = None,
    ):
        self.device_repository = device_repository or DeviceRepository()
        self.stats_service = stats_service or DeviceStatsService()

    async def get_device_statistics(self, device_id: str, days: int = 7) -> Optional[Dict[str, Any]]:
        """Obtém estatísticas detalhadas de um dispositivo"""
        try:
            return await self.device_repository.get_device_statistics(device_id, days)
        except Exception as e:
            logger.exception(f"Erro ao obter estatísticas do dispositivo {device_id}: {e}")
            return None

    async def get_fleet_analytics(self, days: int = 7) -> Dict[str, Any]:
        """Obtém analytics da frota completa de dispositivos"""
        try:
            devices = await self.device_repository.list_devices()

            analytics_calculator = FleetAnalyticsCalculator(self.stats_service)
            return analytics_calculator.calculate_fleet_metrics(devices, days)

        except Exception as e:
            logger.exception(f"Erro ao calcular analytics da frota: {e}")
            return {}

    async def get_location_analytics(self, location: str, days: int = 7) -> Dict[str, Any]:
        """Obtém analytics específicos de uma localização"""
        try:
            devices = await self.device_repository.get_devices_by_location(location)

            analytics_calculator = FleetAnalyticsCalculator(self.stats_service)
            return analytics_calculator.calculate_location_metrics(devices, location, days)

        except Exception as e:
            logger.exception(f"Erro ao calcular analytics da localização {location}: {e}")
            return {}

    async def get_performance_trends(self, device_id: str, days: int = 30) -> Dict[str, Any]:
        """Obtém tendências de performance de um dispositivo"""
        try:
            device = await self.device_repository.get_device(device_id)
            if not device:
                return {}

            activities = await self.device_repository.get_device_activities(device_id, limit=1000)

            trends_calculator = PerformanceTrendsCalculator()
            return trends_calculator.calculate_trends(device, activities, days)

        except Exception as e:
            logger.exception(f"Erro ao calcular tendências do dispositivo {device_id}: {e}")
            return {}

    async def get_health_report(self, device_id: str) -> Dict[str, Any]:
        """Gera relatório de saúde de um dispositivo"""
        try:
            device = await self.device_repository.get_device(device_id)
            if not device:
                return {}

            health_calculator = DeviceHealthCalculator(self.stats_service)
            return health_calculator.generate_health_report(device)

        except Exception as e:
            logger.exception(f"Erro ao gerar relatório de saúde do dispositivo {device_id}: {e}")
            return {}


class FleetAnalyticsCalculator:
    def __init__(self, stats_service: DeviceStatsService):
        self.stats_service = stats_service

    def calculate_fleet_metrics(self, devices: List[Device], days: int) -> Dict[str, Any]:
        """Calcula métricas da frota completa"""
        total_devices = len(devices)
        online_devices = len([d for d in devices if d.status == "online"])

        total_captures = sum(d.stats.get("total_captures", 0) for d in devices)
        total_successful = sum(d.stats.get("successful_captures", 0) for d in devices)
        total_failed = sum(d.stats.get("failed_captures", 0) for d in devices)

        avg_health_score = 0.0
        if devices:
            health_scores = [self.stats_service.get_device_health_score(d) for d in devices]
            avg_health_score = sum(health_scores) / len(health_scores)

        locations = {}
        for device in devices:
            locations[device.location] = locations.get(device.location, 0) + 1

        return {
            "period_days": days,
            "total_devices": total_devices,
            "online_devices": online_devices,
            "offline_devices": total_devices - online_devices,
            "availability_percentage": (online_devices / total_devices * 100) if total_devices > 0 else 0,
            "total_captures": total_captures,
            "successful_captures": total_successful,
            "failed_captures": total_failed,
            "success_rate": (
                (total_successful / (total_successful + total_failed) * 100)
                if (total_successful + total_failed) > 0
                else 0
            ),
            "average_health_score": round(avg_health_score, 2),
            "locations": locations,
            "top_performing_devices": self._get_top_performing_devices(devices, 5),
            "devices_needing_attention": self._get_devices_needing_attention(devices),
        }

    def calculate_location_metrics(self, devices: List[Device], location: str, days: int) -> Dict[str, Any]:
        """Calcula métricas específicas de uma localização"""
        metrics = self.calculate_fleet_metrics(devices, days)
        metrics["location"] = location
        return metrics

    def _get_top_performing_devices(self, devices: List[Device], limit: int) -> List[Dict[str, Any]]:
        """Obtém os dispositivos com melhor performance"""
        device_scores = []
        for device in devices:
            score = self.stats_service.get_device_health_score(device)
            device_scores.append(
                {
                    "device_id": device.device_id,
                    "device_name": device.device_name,
                    "location": device.location,
                    "health_score": round(score, 2),
                    "success_rate": round(self.stats_service.calculate_success_rate(device), 2),
                }
            )

        return sorted(device_scores, key=lambda x: x["health_score"], reverse=True)[:limit]

    def _get_devices_needing_attention(self, devices: List[Device]) -> List[Dict[str, Any]]:
        """Obtém dispositivos que precisam de atenção"""
        attention_devices = []
        for device in devices:
            health_score = self.stats_service.get_device_health_score(device)
            success_rate = self.stats_service.calculate_success_rate(device)

            if health_score < 70 or success_rate < 80 or device.status == "offline":
                attention_devices.append(
                    {
                        "device_id": device.device_id,
                        "device_name": device.device_name,
                        "location": device.location,
                        "status": device.status,
                        "health_score": round(health_score, 2),
                        "success_rate": round(success_rate, 2),
                        "issues": self._identify_issues(device, health_score, success_rate),
                    }
                )

        return sorted(attention_devices, key=lambda x: x["health_score"])

    def _identify_issues(self, device: Device, health_score: float, success_rate: float) -> List[str]:
        """Identifica problemas específicos do dispositivo"""
        issues = []

        if device.status == "offline":
            issues.append("Dispositivo offline")

        if success_rate < 50:
            issues.append("Taxa de sucesso muito baixa")
        elif success_rate < 80:
            issues.append("Taxa de sucesso abaixo do esperado")

        if health_score < 40:
            issues.append("Score de saúde crítico")
        elif health_score < 70:
            issues.append("Score de saúde baixo")

        uptime = device.stats.get("uptime_hours", 0)
        if uptime < 12:
            issues.append("Uptime baixo")

        return issues


class PerformanceTrendsCalculator:
    def calculate_trends(self, device: Device, activities: List[Dict[str, Any]], days: int) -> Dict[str, Any]:
        """Calcula tendências de performance"""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        recent_activities = [a for a in activities if datetime.fromisoformat(a["timestamp"]) > cutoff_date]

        daily_stats = self._calculate_daily_stats(recent_activities, days)

        return {
            "device_id": device.device_id,
            "period_days": days,
            "daily_captures": daily_stats["daily_captures"],
            "daily_success_rates": daily_stats["daily_success_rates"],
            "trend_direction": self._calculate_trend_direction(daily_stats["daily_success_rates"]),
            "average_daily_captures": (
                sum(daily_stats["daily_captures"]) / len(daily_stats["daily_captures"])
                if daily_stats["daily_captures"]
                else 0
            ),
            "peak_performance_day": (
                max(daily_stats["daily_success_rates"]) if daily_stats["daily_success_rates"] else 0
            ),
            "lowest_performance_day": (
                min(daily_stats["daily_success_rates"]) if daily_stats["daily_success_rates"] else 0
            ),
        }

    def _calculate_daily_stats(self, activities: List[Dict[str, Any]], days: int) -> Dict[str, List[float]]:
        """Calcula estatísticas diárias"""
        daily_captures = []
        daily_success_rates = []

        for i in range(days):
            day_start = datetime.now(timezone.utc) - timedelta(days=i + 1)
            day_end = day_start + timedelta(days=1)

            day_activities = [a for a in activities if day_start <= datetime.fromisoformat(a["timestamp"]) < day_end]

            captures = len([a for a in day_activities if "capture" in a["activity_type"]])
            successful = len([a for a in day_activities if a["activity_type"] == "capture_processed"])

            daily_captures.append(captures)
            success_rate = (successful / captures * 100) if captures > 0 else 0
            daily_success_rates.append(success_rate)

        return {
            "daily_captures": list(reversed(daily_captures)),
            "daily_success_rates": list(reversed(daily_success_rates)),
        }

    def _calculate_trend_direction(self, daily_rates: List[float]) -> str:
        """Calcula direção da tendência"""
        if len(daily_rates) < 2:
            return "stable"

        recent_avg = sum(daily_rates[-3:]) / len(daily_rates[-3:]) if len(daily_rates) >= 3 else daily_rates[-1]
        older_avg = sum(daily_rates[:3]) / len(daily_rates[:3]) if len(daily_rates) >= 3 else daily_rates[0]

        if recent_avg > older_avg + 5:
            return "improving"
        elif recent_avg < older_avg - 5:
            return "declining"
        else:
            return "stable"


class DeviceHealthCalculator:
    def __init__(self, stats_service: DeviceStatsService):
        self.stats_service = stats_service

    def generate_health_report(self, device: Device) -> Dict[str, Any]:
        """Gera relatório completo de saúde do dispositivo"""
        health_score = self.stats_service.get_device_health_score(device)
        success_rate = self.stats_service.calculate_success_rate(device)

        return {
            "device_id": device.device_id,
            "device_name": device.device_name,
            "location": device.location,
            "current_status": device.status,
            "health_score": round(health_score, 2),
            "health_status": self._get_health_status(health_score),
            "success_rate": round(success_rate, 2),
            "uptime_hours": device.stats.get("uptime_hours", 0),
            "total_captures": device.stats.get("total_captures", 0),
            "successful_captures": device.stats.get("successful_captures", 0),
            "failed_captures": device.stats.get("failed_captures", 0),
            "last_seen": device.last_seen.isoformat() if device.last_seen else None,
            "recommendations": self._generate_recommendations(device, health_score, success_rate),
            "next_maintenance": self._predict_next_maintenance(device),
        }

    def _get_health_status(self, health_score: float) -> str:
        """Determina status de saúde baseado no score"""
        if health_score >= 90:
            return "excellent"
        elif health_score >= 75:
            return "good"
        elif health_score >= 60:
            return "fair"
        elif health_score >= 40:
            return "poor"
        else:
            return "critical"

    def _generate_recommendations(self, device: Device, health_score: float, success_rate: float) -> List[str]:
        """Gera recomendações baseadas no estado do dispositivo"""
        recommendations = []

        if device.status == "offline":
            recommendations.append("Verificar conectividade de rede")
            recommendations.append("Reiniciar dispositivo se necessário")

        if success_rate < 70:
            recommendations.append("Verificar qualidade da câmera")
            recommendations.append("Limpar lente da câmera")
            recommendations.append("Verificar configurações de captura")

        if health_score < 60:
            recommendations.append("Agendar manutenção preventiva")
            recommendations.append("Verificar logs de erro")

        uptime = device.stats.get("uptime_hours", 0)
        if uptime > 24 * 30:
            recommendations.append("Considerar reinicialização para limpeza de memória")

        return recommendations

    def _predict_next_maintenance(self, device: Device) -> Optional[str]:
        """Prediz próxima manutenção necessária"""
        uptime = device.stats.get("uptime_hours", 0)
        success_rate = self.stats_service.calculate_success_rate(device)

        if success_rate < 50:
            return "imediata"
        elif success_rate < 70:
            return "7_dias"
        elif uptime > 24 * 90:
            return "30_dias"
        else:
            return "90_dias"
