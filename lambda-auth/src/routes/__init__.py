"""
Routes Module - Auth Lambda
Módulo de rotas da API de autenticação
"""

from src.routes.auth_routes import auth_router
from src.routes.user_routes import user_router

__all__ = ["auth_router", "user_router"]
