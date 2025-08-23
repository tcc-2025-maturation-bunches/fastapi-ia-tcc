"""
Routes Module - Request Handler Lambda
Módulo de rotas para endpoints da API
"""

from .combined import combined_router
from .health import health_router
from .storage import storage_router

__all__ = ["health_router", "storage_router", "combined_router"]
