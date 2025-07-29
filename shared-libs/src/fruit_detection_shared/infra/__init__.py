"""
Infrastructure Layer - Fruit Detection Shared
Camada de infraestrutura com clientes externos
"""

from .external import DynamoClient, EC2Client, S3Client, SQSClient

__all__ = [
    "DynamoClient",
    "EC2Client", 
    "S3Client",
    "SQSClient",
]