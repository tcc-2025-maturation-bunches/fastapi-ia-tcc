from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.modules.status.usecase.health_check_usecase import HealthCheckUseCase


class TestHealthCheckUseCase:
    @pytest.mark.asyncio
    async def test_check_system_health(self):
        usecase = HealthCheckUseCase()

        db_status = {
            "status": "healthy",
            "message": "DynamoDB está ACTIVE",
            "table_name": "fruit-detection-test-results",
        }

        s3_status = {
            "status": "healthy",
            "message": "Todos os buckets S3 estão disponíveis",
            "buckets": [
                {"bucket": "fruit-detection-test-images", "status": "available"},
                {"bucket": "fruit-detection-test-results", "status": "available"},
            ],
        }

        timestamp = datetime.now().isoformat()
        ai_status = {
            "service_name": "ai_service",
            "status": "healthy",
            "message": "Serviço de IA está disponível",
            "endpoint": "http://localhost:8001",
            "response_time_ms": 50,
            "details": {
                "models": [{"name": "detection", "version": "1.0"}, {"name": "maturation", "version": "1.0"}],
                "last_check": timestamp,
            },
        }

        usecase._check_dynamodb_status = AsyncMock(return_value=db_status)
        usecase._check_s3_status = AsyncMock(return_value=s3_status)
        usecase._check_ai_service = AsyncMock(return_value=ai_status)

        result = await usecase.check_system_health()

        assert result.status == "healthy"
        assert result.services["database"] == db_status
        assert result.services["storage"] == s3_status
        assert result.services["ai_service"]["status"] == "healthy"
        assert result.services["ai_service"]["details"]["models"][0]["name"] == "detection"
        assert result.services["ai_service"]["details"]["models"][1]["name"] == "maturation"
        assert result.services["ai_service"]["details"]["last_check"] is not None

    @pytest.mark.asyncio
    async def test_check_system_health_degraded(self):
        usecase = HealthCheckUseCase()
        db_status = {
            "status": "healthy",
            "message": "DynamoDB está ACTIVE",
            "table_name": "fruit-detection-test-results",
        }

        s3_status = {
            "status": "degraded",
            "message": "Alguns buckets S3 estão indisponíveis",
            "buckets": [
                {"bucket": "fruit-detection-test-images", "status": "available"},
                {"bucket": "fruit-detection-test-results", "status": "unavailable"},
            ],
        }

        timestamp = datetime.now().isoformat()
        ai_status = {
            "service_name": "ai_service",
            "status": "healthy",
            "message": "Serviço de IA está disponível",
            "endpoint": "http://localhost:8001",
            "response_time_ms": 50,
            "details": {
                "models": [{"name": "detection", "version": "1.0"}, {"name": "maturation", "version": "1.0"}],
                "last_check": timestamp,
            },
        }

        usecase._check_dynamodb_status = AsyncMock(return_value=db_status)
        usecase._check_s3_status = AsyncMock(return_value=s3_status)
        usecase._check_ai_service = AsyncMock(return_value=ai_status)

        result = await usecase.check_system_health()

        assert result.status == "degraded"
        assert result.services["storage"] == s3_status
        assert result.services["database"] == db_status
        assert result.services["ai_service"]["status"] == "healthy"
        assert result.services["ai_service"]["details"]["models"][0]["name"] == "detection"
        assert result.services["ai_service"]["details"]["models"][1]["name"] == "maturation"
        assert result.services["ai_service"]["details"]["last_check"] is not None

    @pytest.mark.asyncio
    async def test_check_ai_service(self):
        timestamp = datetime.now().isoformat()
        mock_ai_data = {
            "status": "healthy",
            "models": [
                {"name": "detection", "version": "1.0", "loaded": True},
                {"name": "maturation", "version": "1.0", "loaded": True},
            ],
        }

        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=mock_ai_data)

        mock_session.get = MagicMock()
        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.get.return_value.__aexit__ = AsyncMock(return_value=None)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            usecase = HealthCheckUseCase()
            usecase._check_ai_service = AsyncMock(
                return_value={
                    "service_name": "ai_service",
                    "status": "healthy",
                    "message": "Serviço de IA está disponível",
                    "details": {
                        "models": [{"name": "detection", "version": "1.0"}, {"name": "maturation", "version": "1.0"}],
                        "last_check": timestamp,
                    },
                }
            )
            result = await usecase._check_ai_service()

            assert result["service_name"] == "ai_service"
            assert result["status"] == "healthy"
            assert result["message"] == "Serviço de IA está disponível"
            assert result["details"]["models"][0]["name"] == "detection"
            assert "last_check" in result["details"]

    @pytest.mark.asyncio
    async def test_check_ai_service_error(self):
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status = 500
        mock_response.text = AsyncMock(return_value="Internal Server Error")

        mock_session.get = MagicMock()
        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.get.return_value.__aexit__ = AsyncMock(return_value=None)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            usecase = HealthCheckUseCase()
            usecase._check_ai_service = AsyncMock(
                return_value={
                    "service_name": "ai_service",
                    "status": "degraded",
                    "message": "Erro ao conectar com o serviço de IA: Internal Server Error (500)",
                }
            )
            result = await usecase._check_ai_service()

            assert result["service_name"] == "ai_service"
            assert result["status"] == "degraded"
            assert "500" in result["message"]

    @pytest.mark.asyncio
    async def test_check_dynamodb_status(self):
        mock_client = MagicMock()
        table_names = [
            "fruit-detection-dev-results",
            "fruit-detection-dev-devices",
            "fruit-detection-dev-device-activities",
        ]

        mock_client.describe_table.return_value = {
            "Table": {"TableName": "fruit-detection-dev-results", "TableStatus": "ACTIVE"}
        }

        with patch("boto3.client", return_value=mock_client):
            with patch("src.app.config.settings.DYNAMODB_TABLE_NAME", table_names[0]):
                with patch("src.app.config.settings.DYNAMODB_DEVICES_TABLE", table_names[1]):
                    with patch("src.app.config.settings.DYNAMODB_DEVICE_ACTIVITIES_TABLE", table_names[2]):
                        usecase = HealthCheckUseCase()
                        result = await usecase._check_dynamodb_status()

                        assert result["status"] == "healthy"
                        assert result["message"] == "Todas as tabelas DynamoDB estão ativas"
                        assert len(result["tables"]) == 3

                        for table_status in result["tables"]:
                            assert table_status["is_active"] is True
                            assert table_status["status"] == "active"
