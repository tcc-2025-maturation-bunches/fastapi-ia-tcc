import pytest

from src.modules.storage.repo.dynamo_repository import DynamoRepository
from src.shared.domain.entities.image import Image
from src.shared.domain.entities.result import DetectionResult, ProcessingResult
from src.shared.domain.enums.ia_model_type_enum import ModelType


class TestDynamoRepository:
    @pytest.mark.asyncio
    async def test_save_image_metadata(self, mock_dynamo_client):
        """Testa o salvamento de metadados de imagem."""
        image = Image(image_url="http://image.url", user_id="user1", image_id="img1")
        repo = DynamoRepository(dynamo_client=mock_dynamo_client)
        await repo.save_image_metadata(image)
        mock_dynamo_client.put_item.assert_called_once()
        called_item = mock_dynamo_client.put_item.call_args[0][0]
        assert called_item["pk"] == f"IMG#{image.image_id}"
        assert called_item["entity_type"] == "IMAGE"

    @pytest.mark.asyncio
    async def test_save_processing_result(self, mock_dynamo_client):
        """Testa o salvamento de um resultado de processamento."""
        result = ProcessingResult(
            image_id="img1",
            model_type=ModelType.COMBINED,
            results=[DetectionResult(class_name="banana", confidence=0.9, bounding_box=[0, 0, 1, 1])],
            request_id="req1",
        )
        repo = DynamoRepository(dynamo_client=mock_dynamo_client)
        await repo.save_processing_result(result)
        mock_dynamo_client.put_item.assert_called_once()
        called_item = mock_dynamo_client.put_item.call_args[0][0]
        assert called_item["pk"] == f"IMG#{result.image_id}"
        assert called_item["sk"] == f"RESULT#{result.request_id}"
        assert called_item["entity_type"] == "RESULT"

    @pytest.mark.asyncio
    async def test_get_image_by_id(self, mock_dynamo_client):
        """Testa a busca de uma imagem por ID."""
        image_id = "img123"
        mock_item = {"image_id": image_id, "user_id": "user1", "image_url": "http://a.b"}
        mock_dynamo_client.get_item.return_value = mock_item
        repo = DynamoRepository(dynamo_client=mock_dynamo_client)
        result = await repo.get_image_by_id(image_id)
        assert isinstance(result, Image)
        assert result.image_id == image_id

    @pytest.mark.asyncio
    async def test_get_result_by_request_id(self, mock_dynamo_client):
        """Testa a busca de um resultado por ID da requisição."""
        req_id = "req123"
        mock_item = {
            "request_id": req_id,
            "image_id": "img1",
            "model_type": "combined",
            "results": [{"class_name": "banana", "confidence": 0.9, "bounding_box": [0, 0, 1, 1]}],
        }
        mock_dynamo_client.query_items.return_value = [mock_item]
        repo = DynamoRepository(dynamo_client=mock_dynamo_client)
        result = await repo.get_result_by_request_id(req_id)
        assert isinstance(result, ProcessingResult)
        assert result.request_id == req_id
