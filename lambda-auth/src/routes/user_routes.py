import logging

from fastapi import APIRouter, status

from src.models.user_model import UserCreate, UserResponse, UserUpdate

logger = logging.getLogger(__name__)

user_router = APIRouter()


@user_router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="Obter usuário por ID",
    description="Recuperar detalhes do usuário pelo ID do usuário",
    tags=["Usuários"],
)
async def get_user(user_id: str):
    pass


@user_router.post(
    "/",
    response_model=UserResponse,
    summary="Criar novo usuário",
    description="Criar um novo usuário com os detalhes fornecidos",
    tags=["Usuários"],
    status_code=status.HTTP_201_CREATED,
)
async def create_user(user: UserCreate):
    pass


@user_router.put(
    "/{user_id}",
    response_model=UserResponse,
    summary="Atualizar usuário",
    description="Atualizar detalhes do usuário pelo ID do usuário",
    tags=["Usuários"],
)
async def update_user(user_id: str, user_update: UserUpdate):
    pass


@user_router.delete(
    "/{user_id}",
    summary="Excluir usuário",
    description="Excluir usuário pelo ID do usuário",
    tags=["Usuários"],
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_user(user_id: str):
    pass
