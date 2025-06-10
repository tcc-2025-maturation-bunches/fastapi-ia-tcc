import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List

import aiohttp
import boto3

from src.app.config import settings
from src.shared.domain.models.status_models import HealthCheckResponse, ServiceStatusResponse

logger = logging.getLogger(__name__)


class HealthCheckUseCase:
    async def check_system_health(self) -> HealthCheckResponse:
        start_time = time.time()

        api_status = {"status": "healthy", "message": "API está funcionando normalmente"}
        db_status = await self._check_dynamodb_status()
        storage_status = await self._check_s3_status()
        ai_status = await self._check_ai_service()

        all_healthy = all(s.get("status") == "healthy" for s in [api_status, db_status, storage_status, ai_status])
        status = "healthy" if all_healthy else "degraded"
        response_time_ms = int((time.time() - start_time) * 1000)

        return HealthCheckResponse(
            status=status,
            timestamp=datetime.now(timezone.utc).isoformat(),
            environment=settings.ENVIRONMENT,
            version=settings.APP_VERSION,
            services={
                "api": api_status,
                "database": db_status,
                "storage": storage_status,
                "ai_service": ai_status,
            },
            response_time_ms=response_time_ms,
        )

    async def check_ai_service(self) -> ServiceStatusResponse:
        start_time = time.time()
        status_data = await self._check_ai_service()
        response_time_ms = int((time.time() - start_time) * 1000)

        models = []
        if status_data.get("status") == "healthy" and "models" in status_data:
            models = status_data["models"]

        return ServiceStatusResponse(
            service_name="ai_service",
            endpoint=settings.EC2_IA_ENDPOINT,
            status=status_data.get("status", "unknown"),
            message=status_data.get("message", ""),
            response_time_ms=response_time_ms,
            details={
                "models": models,
                "last_check": datetime.now(timezone.utc).isoformat(),
            },
        )

    async def _check_dynamodb_status(self) -> Dict[str, Any]:
        try:
            client = boto3.client("dynamodb", region_name=settings.AWS_REGION)
            tables = [
                settings.DYNAMODB_TABLE_NAME,
                settings.DYNAMODB_DEVICES_TABLE,
                settings.DYNAMODB_DEVICE_ACTIVITIES_TABLE,
            ]
            table_statuses = []

            for table in tables:
                try:
                    response = client.describe_table(TableName=table)
                    if response and "Table" in response:
                        table_status = response["Table"]["TableStatus"]
                        table_statuses.append(
                            {"table": table, "status": table_status.lower(), "is_active": table_status == "ACTIVE"}
                        )
                    else:
                        table_statuses.append(
                            {
                                "table": table,
                                "status": "unknown",
                                "is_active": False,
                                "error": "Resposta inválida da API",
                            }
                        )
                except Exception as e:
                    logger.warning(f"Erro ao verificar tabela {table}: {e}")
                    table_statuses.append(
                        {"table": table, "status": "unavailable", "is_active": False, "error": str(e)}
                    )

            all_active = all(t["is_active"] for t in table_statuses)

            return {
                "status": "healthy" if all_active else "degraded",
                "message": (
                    "Todas as tabelas DynamoDB estão ativas"
                    if all_active
                    else "Algumas tabelas DynamoDB não estão ativas"
                ),
                "tables": table_statuses,
            }

        except Exception as e:
            logger.warning(f"Erro ao verificar status do DynamoDB: {e}")
            return {
                "status": "unhealthy",
                "message": f"Erro ao verificar DynamoDB: {str(e)}",
            }

    async def _check_s3_status(self) -> Dict[str, Any]:
        try:
            client = boto3.client("s3", region_name=settings.AWS_REGION)
            buckets = [settings.S3_IMAGES_BUCKET, settings.S3_RESULTS_BUCKET]
            bucket_statuses = []

            for bucket in buckets:
                try:
                    client.head_bucket(Bucket=bucket)
                    bucket_statuses.append({"bucket": bucket, "status": "available"})
                except Exception as e:
                    logger.warning(f"Erro ao verificar bucket {bucket}: {e}")
                    bucket_statuses.append({"bucket": bucket, "status": "unavailable", "error": str(e)})

            all_available = all(b["status"] == "available" for b in bucket_statuses)

            return {
                "status": "healthy" if all_available else "degraded",
                "message": (
                    "Todos os buckets S3 estão disponíveis"
                    if all_available
                    else "Alguns buckets S3 estão indisponíveis"
                ),
                "buckets": bucket_statuses,
            }

        except Exception as e:
            logger.warning(f"Erro ao verificar status do S3: {e}")
            return {
                "status": "unhealthy",
                "message": f"Erro ao verificar S3: {str(e)}",
            }

    async def _check_ai_service(self) -> Dict[str, Any]:
        try:
            health_url = f"{settings.EC2_IA_ENDPOINT}/health"

            async with aiohttp.ClientSession() as session:
                async with session.get(health_url, timeout=settings.REQUEST_TIMEOUT) as response:
                    if response.status == 200:
                        data = await response.json()

                        models: List[Dict[str, Any]] = []
                        if "models" in data:
                            models = data["models"]

                        return {
                            "status": "healthy",
                            "message": "Serviço de IA está disponível",
                            "models": models,
                        }
                    else:
                        error_text = await response.text()
                        return {
                            "status": "degraded",
                            "message": f"Serviço de IA retornou código de status {response.status}: {error_text}",
                        }

        except aiohttp.ClientError as e:
            logger.warning(f"Erro ao conectar ao serviço de IA: {e}")
            return {
                "status": "unhealthy",
                "message": f"Não foi possível conectar ao serviço de IA: {str(e)}",
            }
        except Exception as e:
            logger.warning(f"Erro ao verificar status do serviço de IA: {e}")
            return {
                "status": "unknown",
                "message": f"Erro ao verificar status do serviço de IA: {str(e)}",
            }
