import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from fruit_detection_shared.domain.entities import User
from pwdlib import PasswordHash

from src.repository.dynamo_repository import DynamoRepository

logger = logging.getLogger(__name__)

pwd_context = PasswordHash.recommended()



import asyncio

class UserService:
    def __init__(self, repository: Optional[DynamoRepository] = None):
        self.repository = repository or DynamoRepository()

    async def get_password_hash(self, password: str) -> str:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None, lambda: pwd_context.hash(password)
        )

    async def create_user(self, username: str, password: str, name: str, email: str, user_type: str = "user") -> User:
        try:
            existing_user = await self.repository.get_user_by_username(username)
            if existing_user:
                logger.warning(f"Tentativa de criar usuário duplicado: {username}")
                raise ValueError(f"Usuário com username '{username}' já existe")

            user_id = str(uuid.uuid4())
            password_hash = await self.get_password_hash(password)

            now = datetime.now(timezone.utc)

            user_data = {
                "user_id": user_id,
                "username": username,
                "password_hash": password_hash,
                "name": name,
                "email": email,
                "user_type": user_type,
                "created_at": now.isoformat(),
                "updated_at": now.isoformat(),
            }

            await self.repository.create_user(user_data)

            logger.info(f"Usuário criado com sucesso: {username} (ID: {user_id})")

            return User(
                user_id=user_id,
                username=username,
                name=name,
                email=email,
                user_type=user_type,
                created_at=now,
                updated_at=now,
            )

        except ValueError:
            raise
        except Exception as e:
            logger.exception(f"Erro ao criar usuário: {e}")
            raise

    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        try:
            user_data = await self.repository.get_user_by_id(user_id)

            if not user_data:
                return None

            return User.from_dict(user_data)

        except Exception as e:
            logger.exception(f"Erro ao buscar usuário por ID: {e}")
            raise

    async def get_user_by_username(self, username: str) -> Optional[User]:
        try:
            user_data = await self.repository.get_user_by_username(username)

            if not user_data:
                return None

            return User.from_dict(user_data)

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
        try:
            existing_user_data = await self.repository.get_user_by_id(user_id)
            if not existing_user_data:
                raise ValueError(f"Usuário com ID '{user_id}' não encontrado")

            username = existing_user_data.get("username")

            update_data = {"updated_at": datetime.now(timezone.utc).isoformat()}

            if name:
                update_data["name"] = name
            if email:
                update_data["email"] = email
            if password:
                update_data["password_hash"] = await self.get_password_hash(password)
            if user_type:
                update_data["user_type"] = user_type

            await self.repository.update_user(username, update_data)

            logger.info(f"Usuário atualizado com sucesso: {user_id}")

            updated_user = await self.get_user_by_id(user_id)
            return updated_user

        except ValueError:
            raise
        except Exception as e:
            logger.exception(f"Erro ao atualizar usuário: {e}")
            raise

    async def delete_user(self, user_id: str) -> None:
        try:
            existing_user_data = await self.repository.get_user_by_id(user_id)
            if not existing_user_data:
                raise ValueError(f"Usuário com ID '{user_id}' não encontrado")

            username = existing_user_data.get("username")
            await self.repository.delete_user(username)

            logger.info(f"Usuário deletado com sucesso: {user_id}")

        except ValueError:
            raise
        except Exception as e:
            logger.exception(f"Erro ao deletar usuário: {e}")
            raise
