"""
Routes Module - Results Query Lambda
Módulo de rotas para endpoints da API
"""

from .health import health_router
from .results import results_router

__all__ = ["health_router", "results_router"]
