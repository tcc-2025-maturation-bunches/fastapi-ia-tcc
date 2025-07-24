import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from botocore.exceptions import ClientError
from shared_libs.src.infra.external.sqs.sqs_client import SQSClient
from src.utils.validators import validate_request_id, validate_user_id

from app.config import settings

logger = logging.getLogger(__name__)


class QueueService:
    def __init__(self):
        self.sqs_client = SQSClient(queue_url=settings.SQS_QUEUE_URL)
        self.queue_url = settings.SQS_QUEUE_URL

    async def send_processing_message(
        self,
        image_url: str,
        user_id: str,
        request_id: str,
        metadata: Dict[str, Any],
        result_upload_url: Optional[str] = None,
        maturation_threshold: float = 0.6,
    ) -> Dict[str, Any]:
        try:
            validate_user_id(user_id)
            validate_request_id(request_id)
            message_body = {
                "request_id": request_id,
                "image_url": image_url,
                "user_id": user_id,
                "result_upload_url": result_upload_url,
                "maturation_threshold": maturation_threshold,
                "metadata": metadata,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "source": "request-handler-lambda",
            }

            message_attributes = settings.get_sqs_message_attributes()
            message_attributes.update(
                {
                    "request_id": {"StringValue": request_id, "DataType": "String"},
                    "user_id": {"StringValue": user_id, "DataType": "String"},
                    "processing_type": {"StringValue": "combined", "DataType": "String"},
                }
            )

            response = await self.sqs_client.send_message(
                message_body=message_body,
                message_attributes=message_attributes,
                message_deduplication_id=request_id,
                message_group_id=settings.SQS_MESSAGE_GROUP_ID,
            )

            logger.info(f"Message sent to SQS: {response['MessageId']} for request {request_id}")

            return {"message_id": response["MessageId"], "request_id": request_id, "status": "queued"}

        except ClientError as e:
            logger.exception(f"Error sending message to SQS: {e}")
            raise Exception(f"Failed to queue processing request: {str(e)}")
        except Exception as e:
            logger.exception(f"Unexpected error in queue service: {e}")
            raise

    async def send_batch_messages(self, messages: list[Dict[str, Any]]) -> Dict[str, Any]:
        try:
            entries = []
            for idx, msg in enumerate(messages[:10]):
                entry = {
                    "Id": str(idx),
                    "MessageBody": json.dumps(msg),
                    "MessageDeduplicationId": msg.get("request_id", str(uuid.uuid4())),
                    "MessageGroupId": settings.SQS_MESSAGE_GROUP_ID,
                }

                if "user_id" in msg:
                    entry["MessageAttributes"] = {"user_id": {"StringValue": msg["user_id"], "DataType": "String"}}

                entries.append(entry)

            response = await self.sqs_client.send_message_batch(entries=entries)

            successful = len(response.get("Successful", []))
            failed = len(response.get("Failed", []))

            logger.info(f"Batch send completed: {successful} successful, {failed} failed")

            return {
                "successful": response.get("Successful", []),
                "failed": response.get("Failed", []),
                "total_sent": successful,
                "total_failed": failed,
            }

        except ClientError as e:
            logger.exception(f"Error sending batch messages to SQS: {e}")
            raise Exception(f"Failed to send batch messages: {str(e)}")

    async def get_queue_attributes(self) -> Dict[str, Any]:
        try:
            attributes = await self.sqs_client.get_queue_attributes(
                attribute_names=[
                    "ApproximateNumberOfMessages",
                    "ApproximateNumberOfMessagesNotVisible",
                    "ApproximateNumberOfMessagesDelayed",
                    "CreatedTimestamp",
                    "LastModifiedTimestamp",
                    "QueueArn",
                ]
            )

            return {
                "messages_available": int(attributes.get("ApproximateNumberOfMessages", 0)),
                "messages_in_flight": int(attributes.get("ApproximateNumberOfMessagesNotVisible", 0)),
                "messages_delayed": int(attributes.get("ApproximateNumberOfMessagesDelayed", 0)),
                "queue_arn": attributes.get("QueueArn"),
                "created_at": attributes.get("CreatedTimestamp"),
                "modified_at": attributes.get("LastModifiedTimestamp"),
            }

        except ClientError as e:
            logger.exception(f"Error getting queue attributes: {e}")
            return {"error": str(e), "messages_available": 0, "messages_in_flight": 0}

    def validate_queue_connection(self) -> bool:
        return self.sqs_client.validate_connection()
