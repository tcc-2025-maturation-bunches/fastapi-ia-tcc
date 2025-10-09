import logging
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, status

from src.models.login_model import AuthResponse, LoginRequest
from src.services.auth_service import AuthService

logger = logging.getLogger(__name__)

auth_router = APIRouter()


def get_auth_service() -> AuthService:
    return AuthService()


@auth_router.post(
    "/login",
    response_model=AuthResponse,
    summary="Login do usuário",
    description="Autenticar usuário e emitir token JWT com dados do usuário",
    tags=["Auth"],
    status_code=status.HTTP_200_OK,
)
async def login(login_req: LoginRequest, auth_service: AuthService = Depends(get_auth_service)):
    logger.info(f"Tentativa de login para usuário: {login_req.username}")

    result = await auth_service.login(login_req.username, login_req.password)

    if not result:
        logger.warning(f"Login falhou para usuário: {login_req.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário ou senha inválidos",
            headers={"WWW-Authenticate": "Bearer"},
        )

    logger.info(f"Login bem-sucedido para usuário: {login_req.username}")
    return result


@auth_router.get(
    "/verify",
    summary="Verificar token JWT",
    description="Verificar a validade do token JWT",
    tags=["Auth"],
    status_code=status.HTTP_200_OK,
)
async def verify_token(
        authorization: Optional[str] = Header(None),
        auth_service: AuthService = Depends(get_auth_service)
):
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de autenticação não fornecido",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise ValueError("Esquema de autenticação inválido")
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Formato de token inválido. Use 'Bearer <token>'",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = auth_service.verify_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {
        "valid": True,
        "user": {
            "username": payload.get("sub"),
            "user_id": payload.get("user_id"),
            "user_type": payload.get("user_type"),
            "name": payload.get("name"),
            "email": payload.get("email"),
        },
        "expires_at": payload.get("exp"),
    }


@auth_router.get(
    "/me",
    summary="Obter dados do usuário autenticado",
    description="Retorna dados atualizados do usuário baseado no token",
    tags=["Auth"],
    status_code=status.HTTP_200_OK,
)
async def get_current_user(
        authorization: Optional[str] = Header(None),
        auth_service: AuthService = Depends(get_auth_service)
):
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de autenticação não fornecido",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise ValueError("Esquema de autenticação inválido")
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Formato de token inválido. Use 'Bearer <token>'",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = auth_service.verify_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("user_id")
    user_data = await auth_service.refresh_user_data(user_id)

    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado"
        )

    return user_data