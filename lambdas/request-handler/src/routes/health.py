import logging
from datetime import datetime, timezone
from typing import Any, Dict

import boto3
from botocore.exceptions import ClientError
from fastapi import APIRouter, status

from app.config import settings
from src.services.queue_service import QueueService

logger = logging.getLogger(__name__)

health_router = APIRouter()


@health_router.get("/", response_model=Dict[str, Any])
async def health_check():
    return {
        "status": "healthy",
        "service": "request-handler-lambda",
        "version": settings.SERVICE_VERSION,
        "environment": settings.ENVIRONMENT,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@health_router.get("/detailed", response_model=Dict[str, Any])
async def detailed_health_check():
    health_status = {
        "status": "healthy",
        "service": "request-handler-lambda",
        "version": settings.SERVICE_VERSION,
        "environment": settings.ENVIRONMENT,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "dependencies": {},
    }

    try:
        queue_service = QueueService()
        queue_attrs = await queue_service.get_queue_attributes()
        health_status["dependencies"]["sqs"] = {
            "status": "healthy",
            "queue_url": settings.SQS_QUEUE_URL,
            "messages_available": queue_attrs.get("messages_available", 0),
            "messages_in_flight": queue_attrs.get("messages_in_flight", 0),
        }
    except Exception as e:
        health_status["dependencies"]["sqs"] = {"status": "unhealthy", "error": str(e)}
        health_status["status"] = "degraded"

    try:
        dynamodb = boto3.client("dynamodb", region_name=settings.AWS_REGION)
        response = dynamodb.describe_table(TableName=settings.DYNAMODB_TABLE_NAME)
        table_status = response["Table"]["TableStatus"]

        health_status["dependencies"]["dynamodb"] = {
            "status": "healthy" if table_status == "ACTIVE" else "unhealthy",
            "table_name": settings.DYNAMODB_TABLE_NAME,
            "table_status": table_status,
            "item_count": response["Table"].get("ItemCount", 0),
        }
    except Exception as e:
        health_status["dependencies"]["dynamodb"] = {"status": "unhealthy", "error": str(e)}
        health_status["status"] = "degraded"

    try:
        s3 = boto3.client("s3", region_name=settings.AWS_REGION)
        s3.head_bucket(Bucket=settings.S3_IMAGES_BUCKET)
        images_bucket_status = "healthy"
    except ClientError:
        images_bucket_status = "unhealthy"
        health_status["status"] = "degraded"

    try:
        s3.head_bucket(Bucket=settings.S3_RESULTS_BUCKET)
        results_bucket_status = "healthy"
    except ClientError:
        results_bucket_status = "unhealthy"
        health_status["status"] = "degraded"

    health_status["dependencies"]["s3"] = {
        "images_bucket": {"status": images_bucket_status, "bucket_name": settings.S3_IMAGES_BUCKET},
        "results_bucket": {"status": results_bucket_status, "bucket_name": settings.S3_RESULTS_BUCKET},
    }

    if health_status["status"] == "degraded":
        logger.warning("Health check detected degraded dependencies")

    return health_status


@health_router.get("/ready", status_code=status.HTTP_200_OK)
async def readiness_check():
    try:
        queue_service = QueueService()
        if not queue_service.validate_queue_connection():
            return {"ready": False, "reason": "Cannot connect to SQS queue"}, status.HTTP_503_SERVICE_UNAVAILABLE

        return {"ready": True, "timestamp": datetime.now(timezone.utc).isoformat()}

    except Exception as e:
        logger.exception(f"Readiness check failed: {e}")
        return {"ready": False, "error": str(e)}, status.HTTP_503_SERVICE_UNAVAILABLE


@health_router.get("/live", status_code=status.HTTP_200_OK)
async def liveness_check():
    return {"alive": True, "timestamp": datetime.now(timezone.utc).isoformat()}
