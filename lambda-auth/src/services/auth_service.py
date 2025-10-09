from datetime import timedelta
from typing import Dict, Optional
import logging

from pwdlib import PasswordHash

from src.app.config import settings
from src.repository.dynamo_repository import DynamoRepository
from src.utils.jwt_utils import create_access_token, decode_access_token

logger = logging.getLogger(__name__)

pwd_context = PasswordHash.recommended()

class AuthService:
    def __init__(self, repository: Optional[DynamoRepository] = None):
        self.repository = repository or DynamoRepository()

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str) -> str:
        return pwd_context.hash(password)

    async def authenticate_user(self, username: str, password: str) -> Optional[Dict[str, str]]:
        try:
            user = await self.repository.get_user_by_username(username)

            if not user:
                logger.warning(f"Tentativa de login com username inválido: {username}")
                return None

            if not self.verify_password(password, user.get("password_hash", "")):
                logger.warning(f"Tentativa de login com senha inválida para usuário: {username}")
                return None

            logger.info(f"Usuário autenticado com sucesso: {username}")
            return user

        except Exception as e:
            logger.exception(f"Erro ao autenticar usuário: {e}")
            return None

    def create_token_for_user(self, user: Dict[str, str]) -> Dict[str, str]:
        token_data = {
            "sub": user.get("username"),
            "user_id": user.get("user_id"),
            "user_type": user.get("user_type"),
            "name": user.get("name"),
            "email": user.get("email"),
        }

        access_token = create_access_token(
            data=token_data, 
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        )

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "user": {
                "user_id": user.get("user_id"),
                "username": user.get("username"),
                "name": user.get("name"),
                "email": user.get("email"),
                "user_type": user.get("user_type"),
            }
        }

    async def login(self, username: str, password: str) -> Optional[Dict[str, str]]:
        user = await self.authenticate_user(username, password)

        if not user:
            return None

        return self.create_token_for_user(user)

    def verify_token(self, token: str) -> Optional[Dict[str, str]]:
        return decode_access_token(token)

    async def refresh_user_data(self, user_id: str) -> Optional[Dict[str, str]]:
        try:
            user = await self.repository.get_user_by_id(user_id)
            
            if not user:
                return None
            
            return {
                "user_id": user.get("user_id"),
                "username": user.get("username"),
                "name": user.get("name"),
                "email": user.get("email"),
                "user_type": user.get("user_type"),
            }
        except Exception as e:
            logger.exception(f"Erro ao atualizar dados do usuário: {e}")
            return None