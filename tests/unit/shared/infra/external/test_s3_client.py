import io
from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError

from src.shared.infra.external.s3.s3_client import S3Client


class TestS3Client:
    @pytest.fixture
    def mock_boto3_client(self):
        with patch("boto3.client") as mock_client:
            mock_s3_client = MagicMock()
            mock_client.return_value = mock_s3_client
            yield mock_s3_client

    def test_init_with_defaults(self, mock_boto3_client):
        client = S3Client("test-bucket")
        assert client.bucket_name == "test-bucket"
        assert client.region == "us-east-1"

    def test_init_with_custom_region(self, mock_boto3_client):
        client = S3Client("test-bucket", region="us-west-2")
        assert client.bucket_name == "test-bucket"
        assert client.region == "us-west-2"

    @pytest.mark.asyncio
    async def test_generate_presigned_url_success(self, mock_boto3_client):
        mock_url = "https://test-bucket.s3.amazonaws.com/test-key?presigned-params"
        mock_boto3_client.generate_presigned_url.return_value = mock_url

        client = S3Client("test-bucket")
        key = "test-folder/test-file.jpg"
        content_type = "image/jpeg"
        expires_in = timedelta(minutes=15)

        result = await client.generate_presigned_url(key, content_type, expires_in)

        assert result["upload_url"] == mock_url
        assert result["key"] == key
        assert result["expires_in_seconds"] == 900

        mock_boto3_client.generate_presigned_url.assert_called_once_with(
            "put_object",
            Params={
                "Bucket": "test-bucket",
                "Key": key,
                "ContentType": content_type,
            },
            ExpiresIn=900,
        )

    @pytest.mark.asyncio
    async def test_generate_presigned_url_error(self, mock_boto3_client):
        mock_boto3_client.generate_presigned_url.side_effect = ClientError(
            {"Error": {"Code": "NoSuchBucket", "Message": "Bucket does not exist"}}, "GeneratePresignedUrl"
        )

        client = S3Client("non-existent-bucket")

        with pytest.raises(ClientError):
            await client.generate_presigned_url("test-key", "image/jpeg")

    @pytest.mark.asyncio
    async def test_upload_file_success(self, mock_boto3_client):
        mock_boto3_client.upload_fileobj.return_value = None

        client = S3Client("test-bucket")
        file_obj = io.BytesIO(b"test file content")
        key = "test-folder/test-file.jpg"
        content_type = "image/jpeg"
        metadata = {"user_id": "test-user", "batch": "test-batch"}

        result = await client.upload_file(file_obj, key, content_type, metadata)

        expected_url = "https://test-bucket.s3.us-east-1.amazonaws.com/test-folder/test-file.jpg"
        assert result == expected_url

        mock_boto3_client.upload_fileobj.assert_called_once()
        call_args = mock_boto3_client.upload_fileobj.call_args
        assert call_args[0][0] == file_obj
        assert call_args[0][1] == "test-bucket"
        assert call_args[0][2] == key

        extra_args = call_args[1]["ExtraArgs"]
        assert extra_args["ContentType"] == content_type
        assert extra_args["Metadata"] == metadata

    @pytest.mark.asyncio
    async def test_upload_file_without_content_type(self, mock_boto3_client):
        mock_boto3_client.upload_fileobj.return_value = None

        client = S3Client("test-bucket")
        file_obj = io.BytesIO(b"test content")
        key = "test-file.jpg"

        await client.upload_file(file_obj, key)

        call_args = mock_boto3_client.upload_fileobj.call_args
        extra_args = call_args[1]["ExtraArgs"]
        assert extra_args["ContentType"] == "image/jpeg"

    @pytest.mark.asyncio
    async def test_upload_file_unknown_extension(self, mock_boto3_client):
        mock_boto3_client.upload_fileobj.return_value = None

        client = S3Client("test-bucket")
        file_obj = io.BytesIO(b"test content")
        key = "test-file.unknown"

        await client.upload_file(file_obj, key)

        call_args = mock_boto3_client.upload_fileobj.call_args
        extra_args = call_args[1]["ExtraArgs"]
        assert extra_args["ContentType"] == "application/octet-stream"

    @pytest.mark.asyncio
    async def test_upload_file_error(self, mock_boto3_client):
        mock_boto3_client.upload_fileobj.side_effect = ClientError(
            {"Error": {"Code": "NoSuchBucket", "Message": "Bucket does not exist"}}, "PutObject"
        )

        client = S3Client("non-existent-bucket")
        file_obj = io.BytesIO(b"test content")

        with pytest.raises(ClientError):
            await client.upload_file(file_obj, "test-key")

    @pytest.mark.asyncio
    async def test_get_file_url(self, mock_boto3_client):
        client = S3Client("test-bucket", region="us-west-1")
        key = "folder/subfolder/file.jpg"

        url = await client.get_file_url(key)

        expected_url = "https://test-bucket.s3.us-west-1.amazonaws.com/folder/subfolder/file.jpg"
        assert url == expected_url

    @pytest.mark.asyncio
    async def test_delete_file_success(self, mock_boto3_client):
        mock_boto3_client.delete_object.return_value = None

        client = S3Client("test-bucket")
        key = "test-folder/test-file.jpg"

        result = await client.delete_file(key)

        assert result is True
        mock_boto3_client.delete_object.assert_called_once_with(Bucket="test-bucket", Key=key)

    @pytest.mark.asyncio
    async def test_delete_file_error(self, mock_boto3_client):
        mock_boto3_client.delete_object.side_effect = ClientError(
            {"Error": {"Code": "NoSuchKey", "Message": "Key does not exist"}}, "DeleteObject"
        )

        client = S3Client("test-bucket")

        result = await client.delete_file("non-existent-key")

        assert result is False

    @pytest.mark.asyncio
    async def test_upload_file_with_all_parameters(self, mock_boto3_client):
        mock_boto3_client.upload_fileobj.return_value = None

        client = S3Client("comprehensive-test-bucket", region="eu-west-1")
        file_obj = io.BytesIO(b"comprehensive test content")
        key = "images/2025/06/comprehensive-test.png"
        content_type = "image/png"
        metadata = {
            "user_id": "comprehensive-user",
            "upload_source": "api",
            "batch_id": "batch-12345",
            "quality_check": "passed",
        }

        result = await client.upload_file(file_obj, key, content_type, metadata)

        expected_url = (
            "https://comprehensive-test-bucket.s3.eu-west-1.amazonaws.com/images/2025/06/comprehensive-test.png"
        )
        assert result == expected_url

        call_args = mock_boto3_client.upload_fileobj.call_args
        assert call_args[0][1] == "comprehensive-test-bucket"
        assert call_args[0][2] == key

        extra_args = call_args[1]["ExtraArgs"]
        assert extra_args["ContentType"] == content_type
        assert extra_args["Metadata"] == metadata
        assert len(extra_args["Metadata"]) == 4

    @pytest.mark.asyncio
    async def test_generate_presigned_url_custom_expiry(self, mock_boto3_client):
        mock_url = "https://test-bucket.s3.amazonaws.com/test-key?expires=7200"
        mock_boto3_client.generate_presigned_url.return_value = mock_url

        client = S3Client("test-bucket")
        key = "test-key"
        content_type = "application/json"
        expires_in = timedelta(hours=2)

        result = await client.generate_presigned_url(key, content_type, expires_in)

        assert result["expires_in_seconds"] == 7200

        call_args = mock_boto3_client.generate_presigned_url.call_args
        assert call_args[1]["ExpiresIn"] == 7200

    @pytest.mark.asyncio
    async def test_get_file_url_special_characters(self, mock_boto3_client):
        client = S3Client("test-bucket", region="sa-east-1")
        key = "fotos/maçãs & pêras/análise-2025.jpg"

        url = await client.get_file_url(key)

        expected_url = "https://test-bucket.s3.sa-east-1.amazonaws.com/fotos/maçãs & pêras/análise-2025.jpg"
        assert url == expected_url

    @pytest.mark.asyncio
    async def test_upload_file_no_metadata(self, mock_boto3_client):
        mock_boto3_client.upload_fileobj.return_value = None

        client = S3Client("test-bucket")
        file_obj = io.BytesIO(b"test content")
        key = "test-key"
        content_type = "text/plain"

        await client.upload_file(file_obj, key, content_type)

        call_args = mock_boto3_client.upload_fileobj.call_args
        extra_args = call_args[1]["ExtraArgs"]
        assert "Metadata" not in extra_args
