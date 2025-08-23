"""
External Services - Fruit Detection Shared
Clientes para serviços externos AWS
"""

from .dynamo import DynamoClient
from .ec2 import EC2Client
from .s3 import S3Client
from .sqs import SQSClient

__all__ = [
    "DynamoClient",
    "EC2Client",
    "S3Client",
    "SQSClient",
]
