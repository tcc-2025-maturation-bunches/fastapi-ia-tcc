"""
Repository Module - Processing AI Lambda
Módulo de repositórios para acesso a dados
"""

from .dynamo_repository import DynamoRepository
from .ia_repository import IARepository

__all__ = ["DynamoRepository", "IARepository"]