"""
Device Management - Services Module
Módulo de serviços da aplicação Lambda para integração com Raspberry Pi e API Gateway.
"""

from .device_service import DeviceService

__all__ = [
    "DeviceService",
]
