"""
User Service - Auth Lambda
Serviço responsável por gerenciamento de usuários
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from fruit_detection_shared.domain.entities import User
from pwdlib import PasswordHash

from src.repository.dynamo_repository import DynamoRepository

logger = logging.getLogger(__name__)

# Contexto para hash de senhas usando Argon2
pwd_context = PasswordHash.recommended()


class UserService:
    def __init__(self, repository: Optional[DynamoRepository] = None):
        self.repository = repository or DynamoRepository()

    def get_password_hash(self, password: str) -> str:
        """
        Gera um hash da senha usando Argon2

        Args:
            password: Senha em texto plano

        Returns:
            Hash da senha
        """
        return pwd_context.hash(password)

    async def create_user(self, username: str, password: str, name: str, email: str, user_type: str = "user") -> User:
        """
        Cria um novo usuário no sistema

        Args:
            username: Nome de usuário
            password: Senha em texto plano
            name: Nome completo
            email: E-mail do usuário
            user_type: Tipo de usuário (admin ou user)

        Returns:
            Entidade User criada

        Raises:
            Exception: Se o usuário já existe ou erro ao criar
        """
        try:
            # Verifica se usuário já existe
            existing_user = await self.repository.get_user_by_username(username)
            if existing_user:
                logger.warning(f"Tentativa de criar usuário duplicado: {username}")
                raise ValueError(f"Usuário com username '{username}' já existe")

            user_id = str(uuid.uuid4())
            password_hash = self.get_password_hash(password)

            user_data = {
                "user_id": user_id,
                "username": username,
                "password_hash": password_hash,
                "name": name,
                "email": email,
                "user_type": user_type,
                "createdAt": datetime.now(timezone.utc).isoformat(),
                "updatedAt": datetime.now(timezone.utc).isoformat(),
            }

            await self.repository.create_user(user_data)

            logger.info(f"Usuário criado com sucesso: {username} (ID: {user_id})")

            return User(user_id=user_id, username=username, name=name, email=email, user_type=user_type)

        except ValueError:
            raise
        except Exception as e:
            logger.exception(f"Erro ao criar usuário: {e}")
            raise

    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """
        Busca um usuário pelo ID

        Args:
            user_id: ID do usuário

        Returns:
            Entidade User se encontrado, None caso contrário
        """
        try:
            user_data = await self.repository.get_user_by_id(user_id)

            if not user_data:
                return None

            return User(
                user_id=user_data.get("user_id"),
                username=user_data.get("username"),
                name=user_data.get("name"),
                email=user_data.get("email"),
                user_type=user_data.get("user_type"),
            )

        except Exception as e:
            logger.exception(f"Erro ao buscar usuário por ID: {e}")
            raise

    async def get_user_by_username(self, username: str) -> Optional[User]:
        """
        Busca um usuário pelo username

        Args:
            username: Nome de usuário

        Returns:
            Entidade User se encontrado, None caso contrário
        """
        try:
            user_data = await self.repository.get_user_by_username(username)

            if not user_data:
                return None

            return User(
                user_id=user_data.get("user_id"),
                username=user_data.get("username"),
                name=user_data.get("name"),
                email=user_data.get("email"),
                user_type=user_data.get("user_type"),
            )

        except Exception as e:
            logger.exception(f"Erro ao buscar usuário por username: {e}")
            raise

    async def update_user(
        self,
        user_id: str,
        name: Optional[str] = None,
        email: Optional[str] = None,
        password: Optional[str] = None,
        user_type: Optional[str] = None,
    ) -> User:
        """
        Atualiza dados de um usuário

        Args:
            user_id: ID do usuário
            name: Novo nome (opcional)
            email: Novo e-mail (opcional)
            password: Nova senha em texto plano (opcional)
            user_type: Novo tipo de usuário (opcional)

        Returns:
            Entidade User atualizada

        Raises:
            Exception: Se o usuário não existe ou erro ao atualizar
        """
        try:
            existing_user = await self.repository.get_user_by_id(user_id)
            if not existing_user:
                raise ValueError(f"Usuário com ID '{user_id}' não encontrado")

            update_data = {"updatedAt": datetime.now(timezone.utc).isoformat()}

            if name:
                update_data["name"] = name
            if email:
                update_data["email"] = email
            if password:
                update_data["password_hash"] = self.get_password_hash(password)
            if user_type:
                update_data["user_type"] = user_type

            await self.repository.update_user(user_id, update_data)

            logger.info(f"Usuário atualizado com sucesso: {user_id}")

            # Busca usuário atualizado
            updated_user = await self.get_user_by_id(user_id)
            return updated_user

        except ValueError:
            raise
        except Exception as e:
            logger.exception(f"Erro ao atualizar usuário: {e}")
            raise

    async def delete_user(self, user_id: str) -> None:
        """
        Remove um usuário do sistema

        Args:
            user_id: ID do usuário

        Raises:
            Exception: Se o usuário não existe ou erro ao deletar
        """
        try:
            existing_user = await self.repository.get_user_by_id(user_id)
            if not existing_user:
                raise ValueError(f"Usuário com ID '{user_id}' não encontrado")

            await self.repository.delete_user(user_id)

            logger.info(f"Usuário deletado com sucesso: {user_id}")

        except ValueError:
            raise
        except Exception as e:
            logger.exception(f"Erro ao deletar usuário: {e}")
            raise
