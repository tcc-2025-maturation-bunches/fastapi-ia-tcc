import logging
from typing import Any, Dict

from src.modules.device_monitoring.services.device_config_service import DeviceConfigService

logger = logging.getLogger(__name__)


class DeviceSetupUseCase:
    def __init__(self, config_service: DeviceConfigService = None):
        self.config_service = config_service or DeviceConfigService()

    async def generate_device_config(
        self, device_name: str, location: str, device_type: str, capture_interval: int
    ) -> Dict[str, Any]:
        try:
            setup_result = self.config_service.generate_device_config(
                device_name, location, device_type, capture_interval
            )

            return {
                "device_id": setup_result.device_id,
                "config_script": setup_result.config_script,
                "install_commands": setup_result.install_commands,
                "environment_vars": setup_result.environment_vars,
                "next_steps": setup_result.next_steps,
            }

        except Exception as e:
            logger.exception(f"Erro ao gerar configuração do dispositivo: {e}")
            raise
