"""
Routes Module - Device Management Lambda
Módulo de rotas para endpoints da API de gerenciamento de dispositivos
"""

from .device_routes import device_router
from .health_routes import health_router

__all__ = ["device_router", "health_router"]
