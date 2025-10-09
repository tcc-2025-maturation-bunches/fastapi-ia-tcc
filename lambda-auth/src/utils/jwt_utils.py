"""
Utilities Module - Auth Lambda
Utilitários para JWT e autenticação
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

from jose import JWTError, jwt

from src.app.config import settings

logger = logging.getLogger(__name__)


def create_access_token(data: Dict[str, str], expires_delta: Optional[timedelta] = None) -> str:
    """
    Cria um token JWT com os dados fornecidos

    Args:
        data: Dados a serem incluídos no token (username, user_type, etc)
        expires_delta: Tempo de expiração customizado

    Returns:
        Token JWT como string
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})

    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[Dict[str, str]]:
    """
    Decodifica e valida um token JWT

    Args:
        token: Token JWT a ser decodificado

    Returns:
        Payload do token se válido, None caso contrário
    """
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError as e:
        logger.warning(f"Erro ao decodificar token: {e}")
        return None


def verify_token(token: str) -> bool:
    """
    Verifica se um token JWT é válido

    Args:
        token: Token JWT a ser verificado

    Returns:
        True se o token é válido, False caso contrário
    """
    payload = decode_access_token(token)
    return payload is not None
