from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from src.shared.infra.external.ec2.ec2_client import EC2Client


class TestEC2Client:
    @pytest.mark.asyncio
    async def test_detect_objects_success(self):
        image_url = "https://fruit-analysis-bucket.s3.amazonaws.com/banana_batch_47.jpg"
        result_upload_url = "https://example.com/upload-here"
        metadata = {"user_id": "banana_quality_inspector"}

        mock_response = {"status": "success", "request_id": "req-123"}

        with patch.object(EC2Client, "_make_request", new_callable=AsyncMock) as mock_make_request:
            mock_make_request.return_value = mock_response
            ec2_client = EC2Client(base_url="http://banana-analysis-api.com")

            result = await ec2_client.detect_objects(image_url, result_upload_url, metadata)

            assert result == mock_response

            expected_payload = {
                "image_url": image_url,
                "result_upload_url": result_upload_url,
                "metadata": metadata,
            }
            mock_make_request.assert_called_once_with("http://banana-analysis-api.com/detect", expected_payload)

    @pytest.mark.asyncio
    async def test_make_request_success(self):
        url = "http://banana-analysis-api.com/detect"
        payload = {"image_url": "https://fruit-analysis-bucket.s3.amazonaws.com/banana_ripeness_check.jpg"}
        mock_response = {"status": "success"}

        mock_response_obj = MagicMock()
        mock_response_obj.status = 200
        mock_response_obj.json = AsyncMock(return_value=mock_response)

        mock_response_context = MagicMock()
        mock_response_context.__aenter__ = AsyncMock(return_value=mock_response_obj)
        mock_response_context.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.post = MagicMock(return_value=mock_response_context)

        mock_session_context = MagicMock()
        mock_session_context.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_context.__aexit__ = AsyncMock(return_value=None)

        with patch("aiohttp.ClientSession", return_value=mock_session_context):
            ec2_client = EC2Client()
            result = await ec2_client._make_request(url, payload)

            assert result == mock_response
            mock_session.post.assert_called_once_with(url, json=payload, timeout=ec2_client.timeout)

    @pytest.mark.asyncio
    async def test_make_request_http_error(self):
        url = "http://banana-analysis-api.com/detect"
        payload = {"image_url": "https://fruit-analysis-bucket.s3.amazonaws.com/banana_maturation_batch56.jpg"}
        error_text = "Análise de maturação não disponível"

        mock_response_obj = MagicMock()
        mock_response_obj.status = 404
        mock_response_obj.text = AsyncMock(return_value=error_text)

        mock_response_context = MagicMock()
        mock_response_context.__aenter__ = AsyncMock(return_value=mock_response_obj)
        mock_response_context.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.post = MagicMock(return_value=mock_response_context)

        mock_session_context = MagicMock()
        mock_session_context.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_context.__aexit__ = AsyncMock(return_value=None)

        with patch("aiohttp.ClientSession", return_value=mock_session_context):
            ec2_client = EC2Client()
            result = await ec2_client._make_request(url, payload)

            assert result["status"] == "error"
            assert f"Erro 404: {error_text}" in result["error_message"]
            mock_session.post.assert_called_once_with(url, json=payload, timeout=ec2_client.timeout)

    @pytest.mark.asyncio
    async def test_make_request_connection_error(self):
        url = "http://banana-analysis-api.com/detect"
        payload = {"image_url": "https://fruit-analysis-bucket.s3.amazonaws.com/banana_ripeness_timeline.jpg"}

        mock_session = MagicMock()
        mock_session.__aenter__ = AsyncMock(
            side_effect=aiohttp.ClientError("Erro ao conectar ao serviço de análise de maturação")
        )

        with patch("aiohttp.ClientSession", return_value=mock_session):
            ec2_client = EC2Client()
            result = await ec2_client._make_request(url, payload)

            assert result["status"] == "error"
            assert "Erro de conexão" in result["error_message"]
