"""
Device Management - App Module
Módulo principal da aplicação Lambda para gerenciamento de dispositivos Raspberry Pi.

Este módulo fornece a estrutura principal para:
- Integração com API Gateway via FastAPI
- Gerenciamento de ciclo de vida de dispositivos
- Monitoramento de heartbeat e status
- Configuração e estatísticas de dispositivos
"""

__version__ = "1.0.1"
__description__ = "Lambda para gerenciamento de dispositivos Raspberry Pi via API Gateway"
__author__ = "Device Management Team"
__service_name__ = "device-management-lambda"

from .config import get_settings, settings
from .lambda_handler import lambda_handler
from .main import app

__all__ = ["app", "settings", "get_settings", "lambda_handler", "__version__", "__description__", "__service_name__"]
