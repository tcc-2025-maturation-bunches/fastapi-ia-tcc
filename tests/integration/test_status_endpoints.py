from unittest.mock import AsyncMock, patch

from src.shared.domain.models.status_models import HealthCheckResponse, ServiceStatusResponse


class TestStatusEndpoints:
    def test_health_check(self, client):
        mock_health_status = HealthCheckResponse(
            status="healthy",
            timestamp="2025-05-12T10:30:00Z",
            environment="test",
            version="0.1.0",
            services={
                "api": {"status": "healthy", "message": "API está funcionando normalmente"},
                "database": {
                    "status": "healthy",
                    "message": "DynamoDB está ACTIVE",
                    "table_name": "fruit-detection-test-results",
                },
                "storage": {
                    "status": "healthy",
                    "message": "Todos os buckets S3 estão disponíveis",
                    "buckets": [
                        {"bucket": "fruit-detection-test-images", "status": "available"},
                        {"bucket": "fruit-detection-test-results", "status": "available"},
                    ],
                },
                "ai_service": {
                    "status": "healthy",
                    "message": "Serviço de IA está disponível",
                    "models": [{"name": "detection", "version": "1.0"}, {"name": "maturation", "version": "1.0"}],
                },
            },
            response_time_ms=125,
        )
        with patch(
            "src.modules.status.usecase.health_check_usecase.HealthCheckUseCase.check_system_health",
            new_callable=AsyncMock,
            return_value=mock_health_status,
        ):
            response = client.get("/status/health")

            assert response.status_code == 200
            response_json = response.json()
            assert response_json["status"] == "healthy"
            assert "timestamp" in response_json
            assert "environment" in response_json
            assert "version" in response_json
            assert "services" in response_json
            assert "response_time_ms" in response_json
            assert len(response_json["services"]) == 4
            assert all(service in response_json["services"] for service in ["api", "database", "storage", "ai_service"])
            assert all(
                response_json["services"][service]["status"] == "healthy" for service in response_json["services"]
            )

    def test_health_check_error(self, client):
        with patch(
            "src.modules.status.usecase.health_check_usecase.HealthCheckUseCase.check_system_health",
            new_callable=AsyncMock,
            side_effect=Exception("Error checking system health"),
        ):
            response = client.get("/status/health")

            assert response.status_code == 500
            response_json = response.json()
            assert "detail" in response_json
            assert "Error checking system health" in response_json["detail"]

    def test_ai_service_status(self, client):
        mock_ai_status = ServiceStatusResponse(
            service_name="ai_service",
            endpoint="http://localhost:8001",
            status="healthy",
            message="Serviço de IA está disponível",
            response_time_ms=75,
            details={
                "models": [
                    {"name": "detection", "version": "1.0", "loaded": True},
                    {"name": "maturation", "version": "1.0", "loaded": True},
                ],
                "last_check": "2025-05-12T10:30:00Z",
            },
        )

        with patch(
            "src.modules.status.usecase.health_check_usecase.HealthCheckUseCase.check_ai_service",
            new_callable=AsyncMock,
            return_value=mock_ai_status,
        ):
            response = client.get("/status/ai-service")

            assert response.status_code == 200
            response_json = response.json()
            assert response_json["service_name"] == "ai_service"
            assert response_json["status"] == "healthy"
            assert response_json["endpoint"] == "http://localhost:8001"
            assert "details" in response_json
            assert "models" in response_json["details"]
            assert len(response_json["details"]["models"]) == 2
            assert response_json["details"]["models"][0]["name"] == "detection"
            assert response_json["details"]["models"][1]["name"] == "maturation"

    def test_ai_service_status_error(self, client):
        with patch(
            "src.modules.status.usecase.health_check_usecase.HealthCheckUseCase.check_ai_service",
            new_callable=AsyncMock,
            side_effect=Exception("Error checking AI service"),
        ):
            response = client.get("/status/ai-service")

            assert response.status_code == 500
            response_json = response.json()
            assert "detail" in response_json
            assert "Error checking AI service" in response_json["detail"]

    def test_api_config(self, client):
        response = client.get("/status/config")

        assert response.status_code == 200
        response_json = response.json()
        assert "environment" in response_json
        assert "version" in response_json
        assert "processing_options" in response_json
        assert "upload_options" in response_json
        assert "timestamp" in response_json
        assert "enable_auto_maturation" in response_json["processing_options"]
        assert "min_detection_confidence" in response_json["processing_options"]
        assert "min_maturation_confidence" in response_json["processing_options"]
        assert "max_upload_size_mb" in response_json["upload_options"]
        assert "allowed_image_types" in response_json["upload_options"]
        assert "presigned_url_expiry_minutes" in response_json["upload_options"]
