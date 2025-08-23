from datetime import timedelta
from io import BytesIO

import pytest

from src.modules.storage.repo.s3_repository import S3Repository


class TestS3Repository:
    @pytest.mark.asyncio
    async def test_generate_presigned_url(self, mock_s3_client):
        key = "banana_ripeness_expert/2023/05/12/sample_banana.jpg"
        content_type = "image/jpeg"
        expires_in = timedelta(minutes=15)

        expected_response = {
            "upload_url": "https://fruit-analysis-bucket.s3.amazonaws.com/presigned_url",
            "key": key,
            "expires_in_seconds": 900,
        }
        mock_s3_client.generate_presigned_url.return_value = expected_response

        repo = S3Repository(
            images_bucket="fruit-detection-images", results_bucket="fruit-detection-results", region="us-east-1"
        )
        repo.images_client = mock_s3_client

        result = await repo.generate_presigned_url(key, content_type, expires_in)

        assert result == expected_response
        mock_s3_client.generate_presigned_url.assert_called_once_with(key, content_type, expires_in)

    @pytest.mark.asyncio
    async def test_generate_image_key(self):
        original_filename = "banana_quality_analysis.jpg"
        user_id = "banana_inspector"

        repo = S3Repository()
        key = await repo.generate_image_key(original_filename, user_id)

        parts = key.split("/")
        assert len(parts) == 5
        assert parts[0] == user_id
        assert len(parts[4].split(".")) == 2
        assert parts[4].split(".")[1] == "jpg"

    @pytest.mark.asyncio
    async def test_generate_image_key_without_extension(self):
        original_filename = "banana_ripeness_document"
        user_id = "banana_documents"

        repo = S3Repository()
        key = await repo.generate_image_key(original_filename, user_id)

        assert key.endswith(".jpg")

    @pytest.mark.asyncio
    async def test_upload_file(self, mock_s3_client):
        file_obj = BytesIO(b"banana image content")
        key = "banana_expert/2023/05/12/banana_sample.jpg"
        content_type = "image/jpeg"
        metadata = {"batch": "weekly_shipment_45"}

        expected_url = "https://fruit-analysis-bucket.s3.amazonaws.com/banana_expert/2023/05/12/banana_sample.jpg"
        mock_s3_client.upload_file.return_value = expected_url

        repo = S3Repository()
        repo.images_client = mock_s3_client

        result = await repo.upload_file(file_obj, key, content_type, metadata)

        assert result == expected_url
        mock_s3_client.upload_file.assert_called_once_with(file_obj, key, content_type, metadata)

    @pytest.mark.asyncio
    async def test_upload_result_image(self, mock_s3_client):
        file_obj = BytesIO(b"banana result image")
        original_key = "banana_expert/2023/05/12/banana_original.jpg"
        result_type = "detection"
        content_type = "image/jpeg"
        metadata = {"model_version": "yolov5"}

        expected_result_key = "banana_expert/2023/05/12/banana_original_detection.jpg"
        expected_url = f"https://fruit-analysis-bucket.s3.amazonaws.com/{expected_result_key}"

        mock_s3_client.upload_file.return_value = expected_url

        repo = S3Repository()
        repo.results_client = mock_s3_client

        result = await repo.upload_result_image(file_obj, original_key, result_type, content_type, metadata)

        assert result == expected_url
        mock_s3_client.upload_file.assert_called_once_with(file_obj, expected_result_key, content_type, metadata)

    @pytest.mark.asyncio
    async def test_get_file_url(self, mock_s3_client):
        key = "banana_ripeness/2023/05/12/banana_sample.jpg"
        expected_url = f"https://fruit-analysis-bucket.s3.amazonaws.com/{key}"

        mock_s3_client.get_file_url.return_value = expected_url

        repo = S3Repository()
        repo.images_client = mock_s3_client

        result = await repo.get_file_url(key)

        assert result == expected_url
        mock_s3_client.get_file_url.assert_called_once_with(key)

    @pytest.mark.asyncio
    async def test_get_result_url(self, mock_s3_client):
        key = "banana_ripeness/2023/05/12/banana_result.jpg"
        expected_url = f"https://fruit-analysis-results.s3.amazonaws.com/{key}"

        mock_s3_client.get_file_url.return_value = expected_url

        repo = S3Repository()
        repo.results_client = mock_s3_client

        result = await repo.get_result_url(key)

        assert result == expected_url
        mock_s3_client.get_file_url.assert_called_once_with(key)

    @pytest.mark.asyncio
    async def test_delete_file(self, mock_s3_client):
        key = "banana_ripeness/2023/05/12/banana_to_delete.jpg"

        mock_s3_client.delete_file.return_value = True

        repo = S3Repository()
        repo.images_client = mock_s3_client

        result = await repo.delete_file(key)

        assert result is True
        mock_s3_client.delete_file.assert_called_once_with(key)

    @pytest.mark.asyncio
    async def test_delete_result(self, mock_s3_client):
        key = "banana_ripeness/2023/05/12/banana_result_to_delete.jpg"

        mock_s3_client.delete_file.return_value = True

        repo = S3Repository()
        repo.results_client = mock_s3_client

        result = await repo.delete_result(key)

        assert result is True
        mock_s3_client.delete_file.assert_called_once_with(key)
