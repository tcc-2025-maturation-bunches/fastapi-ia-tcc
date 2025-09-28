import logging
from datetime import datetime, timezone
from typing import Any, Dict

import boto3
from botocore.exceptions import ClientError
from fastapi import APIRouter, status

from src.app.config import settings
from src.services.device_service import DeviceService

logger = logging.getLogger(__name__)

health_router = APIRouter()


@health_router.get("/", response_model=Dict[str, Any])
async def health_check():
    return {
        "status": "healthy",
        "service": "device-management-lambda",
        "version": settings.SERVICE_VERSION,
        "environment": settings.ENVIRONMENT,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@health_router.get("/detailed", response_model=Dict[str, Any])
async def detailed_health_check():
    health_status = {
        "status": "healthy",
        "service": "device-management-lambda",
        "version": settings.SERVICE_VERSION,
        "environment": settings.ENVIRONMENT,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "dependencies": {},
    }

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
        sns = boto3.client("sns", region_name=settings.AWS_REGION)
        topic_arn = settings.SNS_PROCESSING_COMPLETE_TOPIC

        response = sns.get_topic_attributes(TopicArn=topic_arn)

        health_status["dependencies"]["sns"] = {
            "status": "healthy",
            "topic_arn": topic_arn,
            "display_name": response.get("Attributes", {}).get("DisplayName", "Unknown"),
        }
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code")
        health_status["dependencies"]["sns"] = {
            "status": "unhealthy",
            "error": str(e),
            "error_code": error_code,
        }
        if error_code not in ["NotFound", "AuthorizationError"]:
            health_status["status"] = "degraded"
    except Exception as e:
        health_status["dependencies"]["sns"] = {"status": "unhealthy", "error": str(e)}
        health_status["status"] = "degraded"

    try:
        device_service = DeviceService()
        stats = await device_service.get_device_statistics()

        health_status["dependencies"]["device_service"] = {
            "status": "healthy",
            "total_devices": stats.get("total_devices", 0),
            "online_devices": stats.get("online_devices", 0),
            "offline_devices": stats.get("offline_devices", 0),
        }
    except Exception as e:
        health_status["dependencies"]["device_service"] = {"status": "unhealthy", "error": str(e)}
        health_status["status"] = "degraded"

    if health_status["status"] == "degraded":
        logger.warning("Verificação de saúde detectou dependências degradadas")

    return health_status


@health_router.get("/ready", status_code=status.HTTP_200_OK)
async def readiness_check():
    try:
        dynamodb = boto3.client("dynamodb", region_name=settings.AWS_REGION)
        dynamodb.describe_table(TableName=settings.DYNAMODB_TABLE_NAME)

        DeviceService()

        return {"ready": True, "timestamp": datetime.now(timezone.utc).isoformat()}

    except Exception as e:
        logger.exception(f"Verificação de prontidão falhou: {e}")
        return {"ready": False, "error": str(e)}, status.HTTP_503_SERVICE_UNAVAILABLE


@health_router.get("/live", status_code=status.HTTP_200_OK)
async def liveness_check():
    return {"alive": True, "timestamp": datetime.now(timezone.utc).isoformat()}


@health_router.get("/devices-status", response_model=Dict[str, Any])
async def devices_status_check():
    try:
        device_service = DeviceService()
        stats = await device_service.get_device_statistics()

        issues = []
        total_devices = stats.get("total_devices", 0)
        offline_devices = stats.get("offline_devices", 0)
        error_devices = stats.get("error_devices", 0)

        if total_devices == 0:
            issues.append("Nenhum dispositivo registrado")

        if total_devices > 0:
            offline_ratio = offline_devices / total_devices
            if offline_ratio > 0.5:
                issues.append(f"Alta proporção de dispositivos offline: {offline_ratio:.1%}")

            error_ratio = error_devices / total_devices
            if error_ratio > 0.1:
                issues.append(f"Alta proporção de dispositivos com erro: {error_ratio:.1%}")

        return {
            "status": "healthy" if not issues else "warning",
            "statistics": stats,
            "issues": issues,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as e:
        logger.exception(f"Verificação de status dos dispositivos falhou: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
