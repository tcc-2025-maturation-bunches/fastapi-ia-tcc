"""
Routes Module - Auth Lambda
Módulo de rotas da API de autenticação
"""

from .auth_routes import auth_router
from .user_routes import user_router

__all__ = ["auth_router", "user_router"]
