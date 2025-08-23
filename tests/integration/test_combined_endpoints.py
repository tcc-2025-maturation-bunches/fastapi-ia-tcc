from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from src.modules.ia_integration.usecase.combined_processing_usecase import CombinedProcessingUseCase
from src.shared.domain.models.http_models import ProcessingStatusResponse


class TestCombinedEndpointsRefactored:
    @pytest.mark.asyncio
    async def test_process_image_combined_success(self, client: TestClient):
        """
        Testa o início do processamento combinado com sucesso.
        """
        # Payload correto conforme o contrato e o modelo Pydantic
        request_payload = {
            "image_url": "https://bucket.s3.amazonaws.com/images/fruit.jpg",
            "result_upload_url": "https://bucket.s3.amazonaws.com/results/fruit_result.jpg?X-Amz-Signature=...",
            "metadata": {
                "user_id": "user123",
                "image_id": "img-456",
                "location": "warehouse_A",
                "processing_type": "quality_check",
                "notes": "Daily batch inspection",
            },
        }

        # Mock dos métodos do usecase
        with (
            patch.object(
                CombinedProcessingUseCase, "start_processing", new_callable=AsyncMock, return_value="req-combined-123"
            ) as mock_start,
            patch.object(CombinedProcessingUseCase, "execute_in_background", new_callable=AsyncMock) as mock_execute,
        ):

            response = client.post("/combined/process", json=request_payload)

            assert response.status_code == 200
            data = response.json()
            assert data["request_id"] == "req-combined-123"
            assert data["status"] == "processing"

            # Verifica se os métodos foram chamados corretamente
            mock_start.assert_called_once()
            mock_execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_image_combined_missing_metadata(self, client: TestClient):
        """
        Testa a falha no processamento por falta de metadados obrigatórios.
        """
        request_payload = {
            "image_url": "https://bucket.s3.amazonaws.com/images/fruit.jpg",
            "metadata": {
                "user_id": "user123"
                # Faltando image_id e location
            },
        }

        response = client.post("/combined/process", json=request_payload)

        assert response.status_code == 400
        assert "Os seguintes campos são obrigatórios nos metadados: image_id, location" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_processing_status_found(self, client: TestClient):
        """
        Testa a busca de status de um processamento existente.
        """
        request_id = "req-12345"
        mock_status = ProcessingStatusResponse(request_id=request_id, status="completed", progress=1.0)

        with patch.object(
            CombinedProcessingUseCase, "get_processing_status", new_callable=AsyncMock, return_value=mock_status
        ) as mock_get:
            response = client.get(f"/combined/status/{request_id}")

            assert response.status_code == 200
            data = response.json()
            assert data["request_id"] == request_id
            assert data["status"] == "completed"
            mock_get.assert_called_once_with(request_id)

    @pytest.mark.asyncio
    async def test_get_processing_status_not_found(self, client: TestClient):
        """
        Testa a busca de status de um processamento inexistente.
        """
        request_id = "req-not-found"
        with patch.object(
            CombinedProcessingUseCase, "get_processing_status", new_callable=AsyncMock, return_value=None
        ) as mock_get:
            response = client.get(f"/combined/status/{request_id}")

            assert response.status_code == 404
            assert f"Processamento {request_id} não encontrado" in response.json()["detail"]
            mock_get.assert_called_once_with(request_id)

    @pytest.mark.asyncio
    async def test_get_results_by_request_id(self, client: TestClient, sample_combined_result_entity):
        """
        Testa a busca de resultado pelo ID da requisição.
        """
        request_id = "req-combined-9b2f4e"

        mock_result_dict = {
            "status": "success",
            "request_id": request_id,
            "image_id": "test-image-id",
            "image_url": "https://example.com/image.jpg",
            "image_result_url": "https://example.com/result.jpg",
            "user_id": "test-user",
            "createdAt": "2025-06-10T23:04:15.758406+00:00",
            "updatedAt": "2025-06-10T23:04:15.758406+00:00",
            "processing_time_ms": 7864,
            "detection": {
                "summary": {
                    "total_objects": 1,
                    "objects_with_maturation": 1,
                    "detection_time_ms": 153,
                    "maturation_time_ms": 5857,
                    "average_maturation_score": 0.554,
                    "model_versions": {"detection": "yolo11n_v5", "maturation": "maturation-resnet18_v1"},
                },
                "results": [
                    {
                        "class_name": "cachos",
                        "confidence": 0.927,
                        "bounding_box": [0.1731, 0.3739, 0.3622, 0.3718],
                        "maturation_level": {"score": 0.55, "category": "madura"},
                    }
                ],
            },
            "processing_metadata": {
                "image_dimensions": {"width": 624, "height": 468},
                "maturation_distribution": {"verde": 0, "madura": 1, "passada": 0, "nao_analisado": 0},
            },
            "initial_metadata": {"location": "test-location"},
            "additional_metadata": {
                "source": "webcam",
                "timestamp": "2025-06-10T23:03:24.318Z",
                "device_info": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            },
        }

        with patch.object(
            CombinedProcessingUseCase,
            "get_result_by_request_id",
            new_callable=AsyncMock,
            return_value=mock_result_dict,
        ) as mock_get_result:

            response = client.get(f"/combined/results/request/{request_id}")

            assert response.status_code == 200

            data = response.json()
            assert data["request_id"] == request_id
            assert data["status"] == "success"
            assert data["detection"]["summary"]["total_objects"] == 1
            assert data["image_url"] == "https://example.com/image.jpg"
            assert data["user_id"] == "test-user"

            mock_get_result.assert_called_once_with(request_id)
