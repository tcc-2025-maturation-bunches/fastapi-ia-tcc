"""
Repository Module - Results Query Lambda
Módulo de repositórios para acesso a dados
"""

from .dynamo_repository import DynamoRepository

__all__ = ["DynamoRepository"]
