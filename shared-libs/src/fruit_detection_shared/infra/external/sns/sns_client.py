import json
import logging
from typing import Any, Dict, Optional

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class SNSClient:
    def __init__(self, region: str = "us-east-1"):
        self.region = region
        self.client = boto3.client("sns", region_name=self.region)
        logger.info(f"Inicializando cliente SNS na região {self.region}")

    def publish_message(
        self,
        topic_arn: str,
        message: Dict[str, Any],
        subject: Optional[str] = None,
        message_attributes: Optional[Dict[str, Any]] = None,
    ) -> str:
        try:
            publish_params = {
                "TopicArn": topic_arn,
                "Message": json.dumps(message, default=str),
            }

            if subject:
                publish_params["Subject"] = subject

            if message_attributes:
                publish_params["MessageAttributes"] = message_attributes

            response = self.client.publish(**publish_params)

            message_id = response["MessageId"]
            logger.info(f"Mensagem publicada no SNS: {message_id}")
            return message_id

        except ClientError as e:
            logger.error(f"Erro ao publicar no SNS: {e}")
            raise
        except Exception as e:
            logger.error(f"Erro inesperado ao publicar no SNS: {e}")
            raise

    def create_topic(self, topic_name: str, attributes: Optional[Dict[str, str]] = None) -> str:
        try:
            create_params = {"Name": topic_name}

            if attributes:
                create_params["Attributes"] = attributes

            response = self.client.create_topic(**create_params)
            topic_arn = response["TopicArn"]

            logger.info(f"Tópico SNS criado: {topic_arn}")
            return topic_arn

        except ClientError as e:
            logger.error(f"Erro ao criar tópico SNS: {e}")
            raise

    def subscribe_lambda(self, topic_arn: str, lambda_arn: str) -> str:
        try:
            response = self.client.subscribe(TopicArn=topic_arn, Protocol="lambda", Endpoint=lambda_arn)

            subscription_arn = response["SubscriptionArn"]
            logger.info(f"Lambda inscrita no tópico: {subscription_arn}")
            return subscription_arn

        except ClientError as e:
            logger.error(f"Erro ao inscrever Lambda no SNS: {e}")
            raise

    def get_topic_attributes(self, topic_arn: str) -> Dict[str, Any]:
        try:
            response = self.client.get_topic_attributes(TopicArn=topic_arn)
            return response.get("Attributes", {})

        except ClientError as e:
            logger.error(f"Erro ao obter atributos do tópico: {e}")
            raise

    def validate_topic_access(self, topic_arn: str) -> bool:
        try:
            self.get_topic_attributes(topic_arn)
            return True
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code")
            if error_code in ["NotFound", "AuthorizationError"]:
                logger.warning(f"Sem acesso ao tópico {topic_arn}: {error_code}")
                return False
            raise
        except Exception as e:
            logger.error(f"Erro inesperado ao validar acesso ao tópico: {e}")
            return False
