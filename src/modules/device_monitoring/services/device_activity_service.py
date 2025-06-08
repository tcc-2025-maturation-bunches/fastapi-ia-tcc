import logging
from typing import Any, Dict, List

from src.modules.device_monitoring.repo.device_repository import DeviceRepository

logger = logging.getLogger(__name__)


class DeviceActivityService:
    """Serviço responsável por gerenciar atividades e logs dos dispositivos"""

    def __init__(self, device_repository: DeviceRepository):
        self.device_repository = device_repository

    async def log_status_change(self, device_id: str, old_status: str, new_status: str):
        """Registra mudança de status do dispositivo"""
        await self.device_repository.save_device_activity(
            device_id, "status_changed", {"old_status": old_status, "new_status": new_status}
        )

    async def log_device_registration(self, device_id: str, device_name: str, location: str):
        """Registra o registro de um novo dispositivo"""
        await self.device_repository.save_device_activity(
            device_id, "device_registered", {"name": device_name, "location": location}
        )

    async def log_device_update(self, device_id: str, device_name: str, location: str):
        """Registra atualização de dispositivo"""
        await self.device_repository.save_device_activity(
            device_id, "device_updated", {"name": device_name, "location": location}
        )

    async def log_config_update(self, device_id: str, old_config: Dict[str, Any], new_config: Dict[str, Any]):
        """Registra atualização de configuração"""
        await self.device_repository.save_device_activity(
            device_id, "config_updated", {"old_config": old_config, "new_config": new_config}
        )

    async def log_capture_event(self, device_id: str, capture_id: str, event_type: str, details: Dict[str, Any] = None):
        """Registra eventos relacionados a capturas"""
        await self.device_repository.save_device_activity(
            device_id, event_type, {"capture_id": capture_id, **(details or {})}
        )

    async def get_recent_activities(self, device_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Busca atividades recentes do dispositivo"""
        try:
            return await self.device_repository.get_device_activities(device_id, limit)
        except Exception as e:
            logger.exception(f"Erro ao buscar atividades do dispositivo {device_id}: {e}")
            return []

    def format_activity_description(self, activity: Dict[str, Any]) -> str:
        """Formata a descrição de uma atividade para exibição"""
        activity_type = activity["activity_type"]
        details = activity.get("details", {})

        descriptions = {
            "device_registered": "Dispositivo registrado no sistema",
            "device_updated": "Informações do dispositivo atualizadas",
            "device_unregistered": "Dispositivo removido do sistema",
            "status_changed": f"Status alterado: {details.get('old_status', '?')} → {details.get('new_status', '?')}",
            "config_updated": "Configurações atualizadas",
            "capture_uploaded": "Nova imagem capturada e enviada",
            "capture_processed": "Imagem processada com sucesso",
            "capture_failed": "Falha na captura de imagem",
            "heartbeat": "Heartbeat recebido",
            "command_issued": f"Comando enviado: {details.get('command', 'unknown')}",
        }

        return descriptions.get(activity_type, f"Atividade: {activity_type}")
