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

        NOTA: Este teste pode falhar se o ContractResponseMapper não estiver alinhado com a
        entidade CombinedResult, o que indica um bug a ser corrigido na aplicação.
        """
        request_id = "req-combined-9b2f4e"

        with (
            patch.object(
                CombinedProcessingUseCase,
                "get_result_by_request_id",
                new_callable=AsyncMock,
                return_value=sample_combined_result_entity,
            ) as mock_get_result,
            patch("src.shared.mappers.contract_mapper.ContractResponseMapper.to_contract_response") as mock_mapper,
        ):

            mock_mapper.return_value = sample_combined_result_entity.to_contract_dict()

            response = client.get(f"/combined/results/request/{request_id}")

            # O teste espera um 200, mas pode falhar aqui se o mapper estiver quebrado
            assert response.status_code == 200

            data = response.json()
            assert data["request_id"] == request_id
            assert data["status"] == "success"
            assert data["detection"]["summary"]["total_objects"] == 1

            mock_get_result.assert_called_once_with(request_id)
            mock_mapper.assert_called_once()
