import logging

from fastapi import APIRouter, Depends, HTTPException, status

from src.models.user_model import UserCreate, UserResponse, UserUpdate
from src.services.user_service import UserService

logger = logging.getLogger(__name__)

user_router = APIRouter()


def get_user_service() -> UserService:
    """Dependency injection para UserService"""
    return UserService()


@user_router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="Obter usuário por ID",
    description="Recuperar detalhes do usuário pelo ID do usuário",
    tags=["Usuários"],
)
async def get_user(user_id: str, user_service: UserService = Depends(get_user_service)):
    """
    Busca um usuário pelo ID.

    Args:
        user_id: ID do usuário

    Returns:
        Dados do usuário

    Raises:
        HTTPException: Se o usuário não for encontrado
    """
    logger.info(f"Buscando usuário: {user_id}")

    user = await user_service.get_user_by_id(user_id)

    if not user:
        logger.warning(f"Usuário não encontrado: {user_id}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Usuário com ID '{user_id}' não encontrado")

    return UserResponse(
        id=user.user_id, username=user.username, name=user.name, email=user.email, user_type=user.user_type
    )


@user_router.post(
    "/",
    response_model=UserResponse,
    summary="Criar novo usuário",
    description="Criar um novo usuário com os detalhes fornecidos",
    tags=["Usuários"],
    status_code=status.HTTP_201_CREATED,
)
async def create_user(user_data: UserCreate, user_service: UserService = Depends(get_user_service)):
    """
    Cria um novo usuário.

    Args:
        user_data: Dados do usuário a ser criado

    Returns:
        Dados do usuário criado

    Raises:
        HTTPException: Se o usuário já existe ou erro ao criar
    """
    logger.info(f"Criando usuário: {user_data.username}")

    try:
        user = await user_service.create_user(
            username=user_data.username,
            password=user_data.password,
            name=user_data.name,
            email=user_data.email,
            user_type=user_data.user_type,
        )

        logger.info(f"Usuário criado com sucesso: {user.username}")

        return UserResponse(
            id=user.user_id, username=user.username, name=user.name, email=user.email, user_type=user.user_type
        )

    except ValueError as e:
        logger.warning(f"Erro ao criar usuário: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.exception(f"Erro inesperado ao criar usuário: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erro interno ao criar usuário")


@user_router.put(
    "/{user_id}",
    response_model=UserResponse,
    summary="Atualizar usuário",
    description="Atualizar detalhes do usuário pelo ID do usuário",
    tags=["Usuários"],
)
async def update_user(user_id: str, user_update: UserUpdate, user_service: UserService = Depends(get_user_service)):
    """
    Atualiza dados de um usuário.

    Args:
        user_id: ID do usuário
        user_update: Dados a serem atualizados

    Returns:
        Dados do usuário atualizado

    Raises:
        HTTPException: Se o usuário não for encontrado ou erro ao atualizar
    """
    logger.info(f"Atualizando usuário: {user_id}")

    try:
        user = await user_service.update_user(
            user_id=user_id,
            name=user_update.name,
            email=user_update.email,
            password=user_update.password,
            user_type=user_update.user_type,
        )

        logger.info(f"Usuário atualizado com sucesso: {user_id}")

        return UserResponse(
            id=user.user_id, username=user.username, name=user.name, email=user.email, user_type=user.user_type
        )

    except ValueError as e:
        logger.warning(f"Erro ao atualizar usuário: {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.exception(f"Erro inesperado ao atualizar usuário: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erro interno ao atualizar usuário"
        )


@user_router.delete(
    "/{user_id}",
    summary="Excluir usuário",
    description="Excluir usuário pelo ID do usuário",
    tags=["Usuários"],
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_user(user_id: str, user_service: UserService = Depends(get_user_service)):
    """
    Remove um usuário do sistema.

    Args:
        user_id: ID do usuário

    Raises:
        HTTPException: Se o usuário não for encontrado ou erro ao deletar
    """
    logger.info(f"Deletando usuário: {user_id}")

    try:
        await user_service.delete_user(user_id)
        logger.info(f"Usuário deletado com sucesso: {user_id}")

    except ValueError as e:
        logger.warning(f"Erro ao deletar usuário: {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.exception(f"Erro inesperado ao deletar usuário: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erro interno ao deletar usuário")
