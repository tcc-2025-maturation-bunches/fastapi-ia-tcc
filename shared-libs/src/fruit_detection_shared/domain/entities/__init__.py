"""
Domain Entities - Fruit Detection Shared
Entidades de domínio do sistema
"""

from .combined_result import CombinedResult
from .device import Device
from .image import Image
from .user import User

__all__ = [
    "CombinedResult",
    "Device",
    "Image",
    "User",
]
