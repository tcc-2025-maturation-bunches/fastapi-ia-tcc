"""
Authentication Service - Auth Lambda
Serviço responsável por autenticação de usuários
"""

import logging
from datetime import timedelta
from typing import Dict, Optional

from pwdlib import PasswordHash

from src.app.config import settings
from src.repository.dynamo_repository import DynamoRepository
from src.utils.jwt_utils import create_access_token, decode_access_token

logger = logging.getLogger(__name__)

# Contexto para hash de senhas usando Argon2
pwd_context = PasswordHash.recommended()


class AuthService:
    def __init__(self, repository: Optional[DynamoRepository] = None):
        self.repository = repository or DynamoRepository()

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        Verifica se a senha fornecida corresponde ao hash

        Args:
            plain_password: Senha em texto plano
            hashed_password: Senha em hash

        Returns:
            True se a senha está correta, False caso contrário
        """
        return pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str) -> str:
        """
        Gera um hash da senha usando Argon2

        Args:
            password: Senha em texto plano

        Returns:
            Hash da senha
        """
        return pwd_context.hash(password)

    async def authenticate_user(self, username: str, password: str) -> Optional[Dict[str, str]]:
        """
        Autentica um usuário verificando username e senha

        Args:
            username: Nome de usuário
            password: Senha em texto plano

        Returns:
            Dados do usuário se autenticado com sucesso, None caso contrário
        """
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

    def create_token_for_user(self, user: Dict[str, str]) -> str:
        """
        Cria um token JWT para o usuário autenticado

        Args:
            user: Dados do usuário

        Returns:
            Token JWT
        """
        token_data = {
            "sub": user.get("username"),
            "user_id": user.get("user_id"),
            "user_type": user.get("user_type"),
            "name": user.get("name"),
        }

        access_token = create_access_token(
            data=token_data, expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        )

        return access_token

    async def login(self, username: str, password: str) -> Optional[Dict[str, str]]:
        """
        Realiza o login do usuário e retorna o token JWT

        Args:
            username: Nome de usuário
            password: Senha em texto plano

        Returns:
            Dicionário com access_token e informações adicionais, ou None se falhar
        """
        user = await self.authenticate_user(username, password)

        if not user:
            return None

        access_token = self.create_token_for_user(user)

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "user_type": user.get("user_type"),
        }

    def verify_token(self, token: str) -> Optional[Dict[str, str]]:
        """
        Verifica e decodifica um token JWT

        Args:
            token: Token JWT

        Returns:
            Payload do token se válido, None caso contrário
        """
        return decode_access_token(token)
