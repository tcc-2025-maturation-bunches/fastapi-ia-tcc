"""
Routes Module - Results Query Lambda
Módulo de rotas para endpoints da API
"""

from .cache import cache_router
from .health import health_router
from .results import results_router

__all__ = ["cache_router", "health_router", "results_router"]
