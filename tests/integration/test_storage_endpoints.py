from unittest.mock import AsyncMock, patch

from src.modules.storage.usecase.get_result_usecase import GetResultUseCase
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

    def test_get_result_by_request_id(self, client, sample_processing_result_combined):
        request_id = sample_processing_result_combined.request_id

        with patch.object(
            GetResultUseCase,
            "get_by_request_id",
            new_callable=AsyncMock,
            return_value=sample_processing_result_combined,
        ):
            response = client.get(f"/storage/results/request/{request_id}")

            assert response.status_code == 200
            response_json = response.json()
            assert response_json["request_id"] == request_id
            assert response_json["image_id"] == sample_processing_result_combined.image_id
            assert response_json["model_type"] == sample_processing_result_combined.model_type.value
            assert len(response_json["results"]) == 1
            assert response_json["results"][0]["class_name"] == "banana"
            assert response_json["results"][0]["maturation_level"] is not None

    def test_get_result_by_request_id_not_found(self, client):
        request_id = "non-existent-request-id"

        with patch.object(GetResultUseCase, "get_by_request_id", new_callable=AsyncMock, return_value=None):
            response = client.get(f"/storage/results/request/{request_id}")

            assert response.status_code == 404
            assert request_id in response.json()["detail"]

    def test_get_results_by_image_id(self, client, sample_processing_result_combined):
        image_id = sample_processing_result_combined.image_id

        with patch.object(
            GetResultUseCase,
            "get_by_image_id",
            new_callable=AsyncMock,
            return_value=[sample_processing_result_combined],
        ):
            response = client.get(f"/storage/results/image/{image_id}")
            assert response.status_code == 200
            response_json = response.json()
            assert isinstance(response_json, list)
            assert len(response_json) == 1
            assert response_json[0]["model_type"] == "combined"
            assert response_json[0]["image_id"] == image_id

    def test_get_results_by_image_id_not_found(self, client):
        image_id = "non-existent-image-id"
        with patch.object(GetResultUseCase, "get_by_image_id", new_callable=AsyncMock, return_value=[]):
            response = client.get(f"/storage/results/image/{image_id}")

            assert response.status_code == 404
            assert image_id in response.json()["detail"]

    def test_get_results_by_user_id(self, client, sample_processing_result_combined):
        user_id = "banana_results_user"

        with patch.object(
            GetResultUseCase,
            "get_by_user_id",
            new_callable=AsyncMock,
            return_value=[sample_processing_result_combined],
        ):
            response = client.get(f"/storage/results/user/{user_id}")

            assert response.status_code == 200
            response_json = response.json()
            assert isinstance(response_json, list)
            assert len(response_json) == 1
            assert response_json[0]["model_type"] == "combined"

    def test_get_results_by_user_id_not_found(self, client):
        user_id = "non-existent-user-id"

        with patch.object(GetResultUseCase, "get_by_user_id", new_callable=AsyncMock, return_value=[]):
            response = client.get(f"/storage/results/user/{user_id}")

            assert response.status_code == 404
            assert user_id in response.json()["detail"]
