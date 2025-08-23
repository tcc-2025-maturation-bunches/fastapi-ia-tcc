import io
from unittest.mock import AsyncMock

import pytest

from src.modules.storage.usecase.image_upload_usecase import ImageUploadUseCase
from src.shared.domain.entities.image import Image


class TestImageUploadUseCase:
    @pytest.mark.asyncio
    async def test_generate_presigned_url(self, mock_s3_repository, mock_dynamo_repository):
        filename = "banana_maturation_analysis.jpg"
        content_type = "image/jpeg"
        user_id = "banana_quality_control"

        mock_s3_repository.generate_image_key.return_value = (
            "banana_quality_control/2025/05/12/banana-ripeness-uuid.jpg"
        )
        mock_s3_repository.generate_presigned_url.return_value = {
            "upload_url": "https://fruit-analysis-bucket.s3.amazonaws.com/banana-ripeness-key?signature",
            "key": "banana_quality_control/2025/05/12/banana-ripeness-uuid.jpg",
            "expires_in_seconds": 900,
        }

        upload_usecase = ImageUploadUseCase(s3_repository=mock_s3_repository, dynamo_repository=mock_dynamo_repository)
        result = await upload_usecase.generate_presigned_url(filename, content_type, user_id)

        assert "upload_url" in result
        assert "image_id" in result
        assert "expires_in_seconds" in result
        assert result["upload_url"] == "https://fruit-analysis-bucket.s3.amazonaws.com/banana-ripeness-key?signature"
        assert result["expires_in_seconds"] == 900

        mock_s3_repository.generate_image_key.assert_called_once_with(filename, user_id)
        mock_s3_repository.generate_presigned_url.assert_called_once()

    @pytest.mark.asyncio
    async def test_upload_image(self, mock_s3_repository, mock_dynamo_repository):
        file_obj = io.BytesIO(b"banana image content for ripeness analysis")
        filename = "banana_ripeness_stages.jpg"
        user_id = "plantation_inspector"
        content_type = "image/jpeg"
        metadata = {"location": "warehouse_section_3B", "banana_variety": "nanica"}

        mock_s3_repository.generate_image_key.return_value = "plantation_inspector/2025/05/12/banana-analysis-uuid.jpg"
        mock_s3_repository.upload_file.return_value = (
            "https://fruit-analysis-bucket.s3.amazonaws.com/plantation_inspector/2025/05/12/banana-analysis-uuid.jpg"
        )

        upload_usecase = ImageUploadUseCase(s3_repository=mock_s3_repository, dynamo_repository=mock_dynamo_repository)
        image = await upload_usecase.upload_image(file_obj, filename, user_id, content_type, metadata)

        assert isinstance(image, Image)
        assert (
            image.image_url
            == "https://fruit-analysis-bucket.s3.amazonaws.com/plantation_inspector/2025/05/12/banana-analysis-uuid.jpg"
        )
        assert image.user_id == user_id
        assert "original_filename" in image.metadata
        assert "content_type" in image.metadata
        assert "banana_variety" in image.metadata
        assert image.metadata["original_filename"] == filename
        assert image.metadata["content_type"] == content_type
        assert image.metadata["banana_variety"] == "nanica"

        mock_s3_repository.generate_image_key.assert_called_once_with(filename, user_id)
        mock_s3_repository.upload_file.assert_called_once()
        mock_dynamo_repository.save_image_metadata.assert_called_once()

    @pytest.mark.asyncio
    async def test_upload_image_with_s3_error(self, mock_dynamo_repository):
        file_obj = io.BytesIO(b"banana maturation image content")
        filename = "banana_ripeness_batch_47.jpg"
        user_id = "distribution_center_qa"
        content_type = "image/jpeg"

        mock_failing_s3_repository = AsyncMock()
        mock_failing_s3_repository.generate_image_key = AsyncMock(
            return_value="distribution_center_qa/2025/05/12/banana-ripeness-uuid.jpg"
        )
        mock_failing_s3_repository.upload_file = AsyncMock(
            side_effect=Exception("Falha no upload da imagem de maturação")
        )

        upload_usecase = ImageUploadUseCase(
            s3_repository=mock_failing_s3_repository,
            dynamo_repository=mock_dynamo_repository,
        )

        with pytest.raises(Exception) as exc_info:
            await upload_usecase.upload_image(file_obj, filename, user_id, content_type)

        assert "Falha no upload da imagem de maturação" in str(exc_info.value)
        mock_failing_s3_repository.generate_image_key.assert_called_once()
        mock_failing_s3_repository.upload_file.assert_called_once()
        mock_dynamo_repository.save_image_metadata.assert_not_called()

    @pytest.mark.asyncio
    async def test_generate_presigned_url_with_error(self):
        filename = "banana_maturation_timeline.jpg"
        content_type = "image/jpeg"
        user_id = "ripeness_analyst"

        mock_failing_s3_repository = AsyncMock()
        mock_failing_s3_repository.generate_image_key = AsyncMock(
            return_value="ripeness_analyst/2025/05/12/banana-maturation-uuid.jpg"
        )
        mock_failing_s3_repository.generate_presigned_url = AsyncMock(
            side_effect=Exception("Falha na geração da URL para análise de maturação")
        )

        mock_dynamo_repository = AsyncMock()

        upload_usecase = ImageUploadUseCase(
            s3_repository=mock_failing_s3_repository,
            dynamo_repository=mock_dynamo_repository,
        )

        with pytest.raises(Exception) as exc_info:
            await upload_usecase.generate_presigned_url(filename, content_type, user_id)

        assert "Falha na geração da URL para análise de maturação" in str(exc_info.value)
        mock_failing_s3_repository.generate_image_key.assert_called_once()
        mock_failing_s3_repository.generate_presigned_url.assert_called_once()
