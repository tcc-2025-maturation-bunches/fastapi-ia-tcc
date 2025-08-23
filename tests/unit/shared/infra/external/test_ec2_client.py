import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from src.shared.infra.external.ec2.ec2_client import EC2Client


class TestEC2Client:
    @pytest.mark.asyncio
    async def test_client_initialization_with_defaults(self):
        with patch("src.shared.infra.external.ec2.ec2_client.settings") as mock_settings:
            mock_settings.EC2_IA_ENDPOINT = "http://default-endpoint.com"
            mock_settings.REQUEST_TIMEOUT = 30

            ec2_client = EC2Client()

            assert ec2_client.base_url == "http://default-endpoint.com"
            assert ec2_client.timeout == 30
            assert ec2_client.detect_endpoint == "http://default-endpoint.com/detect"
            assert ec2_client.combined_endpoint == "http://default-endpoint.com/process-combined"

    @pytest.mark.asyncio
    async def test_client_initialization_with_custom_parameters(self):
        base_url = "http://custom-endpoint.com"
        timeout = 60

        ec2_client = EC2Client(base_url=base_url, timeout=timeout)

        assert ec2_client.base_url == base_url
        assert ec2_client.timeout == timeout
        assert ec2_client.detect_endpoint == "http://custom-endpoint.com/detect"
        assert ec2_client.combined_endpoint == "http://custom-endpoint.com/process-combined"

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
    async def test_make_request_http_error_500(self):
        url = "http://banana-analysis-api.com/detect"
        payload = {"image_url": "https://fruit-analysis-bucket.s3.amazonaws.com/banana_maturation_batch56.jpg"}
        error_text = "Internal Server Error"

        mock_response_obj = MagicMock()
        mock_response_obj.status = 500
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
            assert f"Erro 500: {error_text}" in result["error_message"]
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

    @pytest.mark.asyncio
    async def test_make_request_timeout_error(self):
        url = "http://banana-analysis-api.com/detect"
        payload = {"image_url": "https://fruit-analysis-bucket.s3.amazonaws.com/timeout_test.jpg"}

        mock_session = MagicMock()
        mock_session.__aenter__ = AsyncMock(side_effect=asyncio.TimeoutError("Request timeout"))

        with patch("aiohttp.ClientSession", return_value=mock_session):
            ec2_client = EC2Client()
            result = await ec2_client._make_request(url, payload)

            assert result["status"] == "error"
            assert "Erro inesperado" in result["error_message"]

    @pytest.mark.asyncio
    async def test_make_request_unexpected_exception(self):
        url = "http://banana-analysis-api.com/detect"
        payload = {"image_url": "https://fruit-analysis-bucket.s3.amazonaws.com/exception_test.jpg"}

        mock_session = MagicMock()
        mock_session.__aenter__ = AsyncMock(side_effect=ValueError("Unexpected error"))

        with patch("aiohttp.ClientSession", return_value=mock_session):
            ec2_client = EC2Client()
            result = await ec2_client._make_request(url, payload)

            assert result["status"] == "error"
            assert "Erro inesperado" in result["error_message"]
            assert "Unexpected error" in result["error_message"]

    @pytest.mark.asyncio
    async def test_make_request_json_decode_error(self):
        url = "http://banana-analysis-api.com/detect"
        payload = {"image_url": "https://fruit-analysis-bucket.s3.amazonaws.com/invalid_json.jpg"}

        mock_response_obj = MagicMock()
        mock_response_obj.status = 200
        mock_response_obj.json = AsyncMock(side_effect=ValueError("Invalid JSON"))

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
            assert "Erro inesperado" in result["error_message"]
