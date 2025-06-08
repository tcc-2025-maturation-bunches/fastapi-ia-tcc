import pytest

from src.modules.ia_integration.repo.ia_repository import IARepository
from src.shared.domain.entities.combined_result import CombinedResult
from src.shared.domain.entities.image import Image


class TestIARepositoryRefactored:

    @pytest.mark.asyncio
    async def test_process_combined_success(self, mock_ec2_client, sample_ec2_combined_response):
        """Testa o método process_combined do repositório em caso de sucesso."""
        ia_repository = IARepository(ec2_client=mock_ec2_client)
        image = Image(
            image_url="https://bucket.s3.amazonaws.com/images/fruit.jpg", user_id="user123", image_id="img-456"
        )
        result_upload_url = "http://s3-upload.url/result"

        result_entity = await ia_repository.process_combined(image, result_upload_url)

        assert isinstance(result_entity, CombinedResult)
        assert result_entity.status == "success"
        assert result_entity.request_id == sample_ec2_combined_response["request_id"]
        assert result_entity.detection.summary.total_objects == 1
        assert result_entity.processing_metadata.maturation_distribution.madura == 1

        mock_ec2_client.process_combined.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_combined_error_from_ec2(self, mock_ec2_client):
        """Testa o tratamento de erro quando o EC2Client retorna um erro."""
        error_response = {
            "status": "error",
            "request_id": "req-error-123",
            "error_code": "IMAGE_PROCESSING_ERROR",
            "error_message": "Failed to process image",
            "error_details": {"original_error": "Unsupported format"},
            "detection": {
                "results": [],
                "summary": {
                    "total_objects": 0,
                    "objects_with_maturation": 0,
                    "detection_time_ms": 0,
                    "maturation_time_ms": 0,
                    "average_maturation_score": 0.0,
                    "model_versions": {"detection": "unknown", "maturation": "unknown"},
                },
            },
            "image_result_url": None,
            "processing_time_ms": 0,
            "processing_metadata": None,
        }
        mock_ec2_client.process_combined.return_value = error_response

        ia_repository = IARepository(ec2_client=mock_ec2_client)
        image = Image(image_url="some.webp", user_id="user1")

        result_entity = await ia_repository.process_combined(image, "some_url")

        assert isinstance(result_entity, CombinedResult)
        assert result_entity.status == "error"
        assert result_entity.error_code == "IMAGE_PROCESSING_ERROR"
