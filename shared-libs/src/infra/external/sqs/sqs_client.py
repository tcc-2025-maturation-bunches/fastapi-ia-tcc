import json
import logging
from typing import Any, Dict, List, Optional

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class SQSClient:
    def __init__(self, queue_url: str, region: Optional[str] = None):
        self.queue_url = queue_url
        self.region = region or "us-east-1"
        self.client = boto3.client("sqs", region_name=self.region)
        logger.info(f"Inicializando cliente SQS para fila {self.queue_url}")

    async def send_message(
        self,
        message_body: Dict[str, Any],
        message_attributes: Optional[Dict[str, Any]] = None,
        message_deduplication_id: Optional[str] = None,
        message_group_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        try:
            params = {
                "QueueUrl": self.queue_url,
                "MessageBody": json.dumps(message_body),
            }

            if message_attributes:
                params["MessageAttributes"] = message_attributes

            if message_deduplication_id:
                params["MessageDeduplicationId"] = message_deduplication_id

            if message_group_id:
                params["MessageGroupId"] = message_group_id

            response = self.client.send_message(**params)

            logger.info(f"Mensagem enviada: {response['MessageId']}")
            return response

        except ClientError as e:
            logger.error(f"Erro ao enviar mensagem para SQS: {e}")
            raise

    async def send_message_batch(self, entries: List[Dict[str, Any]]) -> Dict[str, Any]:
        try:
            response = self.client.send_message_batch(QueueUrl=self.queue_url, Entries=entries)

            successful = len(response.get("Successful", []))
            failed = len(response.get("Failed", []))

            logger.info(f"Batch enviado: {successful} sucesso, {failed} falha")
            return response

        except ClientError as e:
            logger.error(f"Erro ao enviar batch para SQS: {e}")
            raise

    async def get_queue_attributes(self, attribute_names: Optional[List[str]] = None) -> Dict[str, Any]:
        try:
            if not attribute_names:
                attribute_names = [
                    "ApproximateNumberOfMessages",
                    "ApproximateNumberOfMessagesNotVisible",
                    "ApproximateNumberOfMessagesDelayed",
                    "CreatedTimestamp",
                    "LastModifiedTimestamp",
                    "QueueArn",
                ]

            response = self.client.get_queue_attributes(QueueUrl=self.queue_url, AttributeNames=attribute_names)

            return response.get("Attributes", {})

        except ClientError as e:
            logger.error(f"Erro ao obter atributos da fila: {e}")
            raise

    def validate_connection(self) -> bool:
        try:
            self.client.get_queue_attributes(QueueUrl=self.queue_url, AttributeNames=["QueueArn"])
            return True
        except ClientError:
            logger.error(f"Falha ao conectar à fila: {self.queue_url}")
            return False
