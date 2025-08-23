import pytest

from src.modules.storage.repo.dynamo_repository import DynamoRepository
from src.shared.domain.entities.image import Image


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
