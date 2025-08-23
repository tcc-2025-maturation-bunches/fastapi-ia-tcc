from unittest.mock import AsyncMock, patch

from src.modules.storage.usecase.image_upload_usecase import ImageUploadUseCase
from src.shared.domain.entities.image import Image


class TestStorageEndpoints:
    def test_generate_presigned_url(self, client):
        request_data = {
            "filename": "banana_quality_check.jpg",
            "content_type": "image/jpeg",
            "user_id": "banana_quality_inspector",
        }

        expected_response = {
            "upload_url": "https://fruit-detection-test-images.s3.amazonaws.com/presigned-url",
            "image_id": "banana-upload-id-123",
            "expires_in_seconds": 900,
        }

        with patch.object(
            ImageUploadUseCase, "generate_presigned_url", new_callable=AsyncMock, return_value=expected_response
        ):
            response = client.post("/storage/presigned-url", json=request_data)

            assert response.status_code == 200
            response_json = response.json()
            assert response_json["upload_url"] == expected_response["upload_url"]
            assert response_json["image_id"] == expected_response["image_id"]
            assert response_json["expires_in_seconds"] == expected_response["expires_in_seconds"]

    def test_upload_image(self, client, sample_upload_file):
        mock_response = {
            "image_id": "banana-upload-id-456",
            "image_url": "https://fruit-detection-test-images.s3.amazonaws.com/banana_quality.jpg",
            "message": "Imagem enviada com sucesso",
        }

        mock_image = Image(
            image_url=mock_response["image_url"], user_id="banana_upload_user", image_id=mock_response["image_id"]
        )

        with patch.object(ImageUploadUseCase, "upload_image", new_callable=AsyncMock, return_value=mock_image):
            response = client.post(
                "/storage/upload",
                files={"file": ("banana_quality.jpg", b"file content", "image/jpeg")},
                data={"user_id": "banana_upload_user", "metadata": '{"batch": "banana_shipment_45"}'},
            )

            assert response.status_code == 200
            response_json = response.json()
            assert response_json["image_id"] == mock_response["image_id"]
            assert response_json["image_url"] == mock_response["image_url"]
            assert response_json["message"] == mock_response["message"]
