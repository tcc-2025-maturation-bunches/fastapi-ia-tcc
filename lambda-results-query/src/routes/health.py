import logging
import time
from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError
from fastapi import APIRouter, HTTPException, status
from fruit_detection_shared.domain.models import HealthCheckResponse, ServiceStatusResponse

from src.app.config import settings

logger = logging.getLogger(__name__)

health_router = APIRouter()


@health_router.get("/", response_model=HealthCheckResponse)
async def health_check():
    start_time = time.time()

    health_data = {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "environment": settings.ENVIRONMENT,
        "version": settings.SERVICE_VERSION,
        "services": {"api": {"status": "healthy", "message": "API está funcionando normalmente"}},
        "response_time_ms": int((time.time() - start_time) * 1000),
    }

    return HealthCheckResponse(**health_data)


@health_router.get("/detailed", response_model=HealthCheckResponse)
async def detailed_health_check():
    start_time = time.time()
    services_status = {}
    overall_status = "healthy"

    try:
        dynamodb = boto3.client("dynamodb", region_name=settings.AWS_REGION)
        response = dynamodb.describe_table(TableName=settings.DYNAMODB_TABLE_NAME)
        table_status = response["Table"]["TableStatus"]

        services_status["dynamodb"] = {
            "status": "healthy" if table_status == "ACTIVE" else "unhealthy",
            "table_name": settings.DYNAMODB_TABLE_NAME,
            "table_status": table_status,
            "item_count": response["Table"].get("ItemCount", 0),
        }
    except Exception as e:
        services_status["dynamodb"] = {"status": "unhealthy", "error": str(e)}
        overall_status = "degraded"

    try:
        s3 = boto3.client("s3", region_name=settings.AWS_REGION)
        s3.head_bucket(Bucket=settings.S3_RESULTS_BUCKET)
        results_bucket_status = "healthy"
    except ClientError:
        results_bucket_status = "unhealthy"
        overall_status = "degraded"

    services_status["s3"] = {
        "results_bucket": {"status": results_bucket_status, "bucket_name": settings.S3_RESULTS_BUCKET}
    }

    if overall_status == "degraded":
        logger.warning("Health check detected degraded dependencies")

    health_data = {
        "status": overall_status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "environment": settings.ENVIRONMENT,
        "version": settings.SERVICE_VERSION,
        "services": services_status,
        "response_time_ms": int((time.time() - start_time) * 1000),
    }

    return HealthCheckResponse(**health_data)


@health_router.get("/ready", status_code=status.HTTP_200_OK)
async def readiness_check():
    try:
        dynamodb = boto3.client("dynamodb", region_name=settings.AWS_REGION)
        dynamodb.describe_table(TableName=settings.DYNAMODB_TABLE_NAME)

        return {"ready": True, "timestamp": datetime.now(timezone.utc).isoformat()}

    except Exception as e:
        logger.exception(f"Readiness check failed: {e}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail={"ready": False, "error": str(e)})


@health_router.get("/live", status_code=status.HTTP_200_OK)
async def liveness_check():
    return {"alive": True, "timestamp": datetime.now(timezone.utc).isoformat()}


@health_router.get("/services", response_model=list[ServiceStatusResponse])
async def services_status():
    services = []

    start_time = time.time()
    try:
        dynamodb = boto3.client("dynamodb", region_name=settings.AWS_REGION)
        response = dynamodb.describe_table(TableName=settings.DYNAMODB_TABLE_NAME)
        table_status = response["Table"]["TableStatus"]

        services.append(
            ServiceStatusResponse(
                service_name="DynamoDB",
                endpoint=f"Table: {settings.DYNAMODB_TABLE_NAME}",
                status="healthy" if table_status == "ACTIVE" else "unhealthy",
                message=f"Table status: {table_status}",
                response_time_ms=int((time.time() - start_time) * 1000),
                details={
                    "table_name": settings.DYNAMODB_TABLE_NAME,
                    "table_status": table_status,
                    "item_count": response["Table"].get("ItemCount", 0),
                },
            )
        )
    except Exception as e:
        services.append(
            ServiceStatusResponse(
                service_name="DynamoDB",
                endpoint=f"Table: {settings.DYNAMODB_TABLE_NAME}",
                status="unhealthy",
                message=f"Error: {str(e)}",
                response_time_ms=int((time.time() - start_time) * 1000),
                details={"error": str(e)},
            )
        )

    start_time = time.time()
    try:
        s3 = boto3.client("s3", region_name=settings.AWS_REGION)
        s3.head_bucket(Bucket=settings.S3_RESULTS_BUCKET)

        services.append(
            ServiceStatusResponse(
                service_name="S3",
                endpoint=f"Bucket: {settings.S3_RESULTS_BUCKET}",
                status="healthy",
                message="Bucket is accessible",
                response_time_ms=int((time.time() - start_time) * 1000),
                details={"bucket_name": settings.S3_RESULTS_BUCKET},
            )
        )
    except ClientError as e:
        services.append(
            ServiceStatusResponse(
                service_name="S3",
                endpoint=f"Bucket: {settings.S3_RESULTS_BUCKET}",
                status="unhealthy",
                message=f"Bucket not accessible: {str(e)}",
                response_time_ms=int((time.time() - start_time) * 1000),
                details={"bucket_name": settings.S3_RESULTS_BUCKET, "error": str(e)},
            )
        )

    return services
