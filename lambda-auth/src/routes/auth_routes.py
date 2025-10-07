import logging

from fastapi import APIRouter, Depends
from fastapi_jwt_auth import AuthJWT

from src.models.login_model import AuthResponse, LoginRequest

logger = logging.getLogger(__name__)

auth_router = APIRouter()


@auth_router.post(
    "/login",
    responses=AuthResponse,
    summary="Login do usuário",
    description="Autenticar usuário e emitir token JWT",
    tags=["Auth"],
)
def login(login_req: LoginRequest, Authorize: AuthJWT = Depends()):
    pass


@auth_router.get(
    "/refresh",
    response_model=AuthResponse,
    summary="Atualizar token JWT",
    description="Atualizar token JWT usando um token de atualização válido",
    tags=["Auth"],
)
def refresh_token(Authorize: AuthJWT = Depends()):
    pass


@auth_router.get(
    "/verify",
    summary="Verificar token JWT",
    description="Verificar a validade do token JWT",
    tags=["Auth"],
)
def verify_token(Authorize: AuthJWT = Depends()):
    pass
