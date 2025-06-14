import asyncio
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
    async def test_detect_objects_without_metadata(self):
        image_url = "https://fruit-analysis-bucket.s3.amazonaws.com/banana_batch_48.jpg"
        result_upload_url = "https://example.com/upload-here"

        mock_response = {"status": "success", "request_id": "req-124"}

        with patch.object(EC2Client, "_make_request", new_callable=AsyncMock) as mock_make_request:
            mock_make_request.return_value = mock_response
            ec2_client = EC2Client(base_url="http://banana-analysis-api.com")

            result = await ec2_client.detect_objects(image_url, result_upload_url)

            assert result == mock_response

            expected_payload = {
                "image_url": image_url,
                "result_upload_url": result_upload_url,
                "metadata": {},
            }
            mock_make_request.assert_called_once_with("http://banana-analysis-api.com/detect", expected_payload)

    @pytest.mark.asyncio
    async def test_process_combined_success(self):
        image_url = "https://fruit-analysis-bucket.s3.amazonaws.com/apple_batch_12.jpg"
        result_upload_url = "https://example.com/upload-combined"
        maturation_threshold = 0.7
        metadata = {"user_id": "apple_quality_inspector", "batch": "batch_12"}

        mock_response = {"status": "success", "request_id": "req-combined-456"}

        with patch.object(EC2Client, "_make_request", new_callable=AsyncMock) as mock_make_request:
            mock_make_request.return_value = mock_response
            ec2_client = EC2Client(base_url="http://fruit-analysis-api.com")

            result = await ec2_client.process_combined(image_url, result_upload_url, maturation_threshold, metadata)

            assert result == mock_response

            expected_payload = {
                "image_url": image_url,
                "result_upload_url": result_upload_url,
                "maturation_threshold": maturation_threshold,
                "metadata": metadata,
            }
            mock_make_request.assert_called_once_with(
                "http://fruit-analysis-api.com/process-combined", expected_payload
            )

    @pytest.mark.asyncio
    async def test_process_combined_default_parameters(self):
        image_url = "https://fruit-analysis-bucket.s3.amazonaws.com/orange_batch_33.jpg"
        result_upload_url = "https://example.com/upload-combined"

        mock_response = {"status": "success", "request_id": "req-combined-789"}

        with patch.object(EC2Client, "_make_request", new_callable=AsyncMock) as mock_make_request:
            mock_make_request.return_value = mock_response
            ec2_client = EC2Client(base_url="http://fruit-analysis-api.com")

            result = await ec2_client.process_combined(image_url, result_upload_url)

            assert result == mock_response

            expected_payload = {
                "image_url": image_url,
                "result_upload_url": result_upload_url,
                "maturation_threshold": 0.6,
                "metadata": {},
            }
            mock_make_request.assert_called_once_with(
                "http://fruit-analysis-api.com/process-combined", expected_payload
            )

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

    @pytest.mark.asyncio
    async def test_detect_objects_with_error_response(self):
        image_url = "https://fruit-analysis-bucket.s3.amazonaws.com/error_image.jpg"
        result_upload_url = "https://example.com/upload-error"
        metadata = {"user_id": "error_test"}

        mock_error_response = {"status": "error", "error_message": "Erro 500: Service temporarily unavailable"}

        with patch.object(EC2Client, "_make_request", new_callable=AsyncMock) as mock_make_request:
            mock_make_request.return_value = mock_error_response
            ec2_client = EC2Client(base_url="http://banana-analysis-api.com")

            result = await ec2_client.detect_objects(image_url, result_upload_url, metadata)

            assert result == mock_error_response
            assert result["status"] == "error"

    @pytest.mark.asyncio
    async def test_process_combined_with_error_response(self):
        image_url = "https://fruit-analysis-bucket.s3.amazonaws.com/error_combined.jpg"
        result_upload_url = "https://example.com/upload-error"
        maturation_threshold = 0.8

        mock_error_response = {"status": "error", "error_message": "Erro de conexão: Connection refused"}

        with patch.object(EC2Client, "_make_request", new_callable=AsyncMock) as mock_make_request:
            mock_make_request.return_value = mock_error_response
            ec2_client = EC2Client(base_url="http://banana-analysis-api.com")

            result = await ec2_client.process_combined(image_url, result_upload_url, maturation_threshold)

            assert result == mock_error_response
            assert result["status"] == "error"

    @pytest.mark.asyncio
    async def test_make_request_with_custom_timeout(self):
        url = "http://banana-analysis-api.com/detect"
        payload = {"image_url": "https://fruit-analysis-bucket.s3.amazonaws.com/timeout_test.jpg"}
        mock_response = {"status": "success", "processing_time": "fast"}
        custom_timeout = 120

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
            ec2_client = EC2Client(timeout=custom_timeout)
            result = await ec2_client._make_request(url, payload)

            assert result == mock_response
            mock_session.post.assert_called_once_with(url, json=payload, timeout=custom_timeout)

    @pytest.mark.asyncio
    async def test_endpoint_construction(self):
        base_url = "https://production-ai-api.company.com"
        ec2_client = EC2Client(base_url=base_url)

        assert ec2_client.detect_endpoint == f"{base_url}/detect"
        assert ec2_client.combined_endpoint == f"{base_url}/process-combined"

    @pytest.mark.asyncio
    async def test_payload_construction_detect_objects(self):
        image_url = "https://test-bucket.s3.amazonaws.com/test-image.jpg"
        result_upload_url = "https://result-bucket.s3.amazonaws.com/result.json"
        metadata = {"user_id": "test-user-123", "batch_id": "batch-456", "timestamp": "2025-06-14T10:30:00Z"}

        with patch.object(EC2Client, "_make_request", new_callable=AsyncMock) as mock_make_request:
            mock_make_request.return_value = {"status": "success"}
            ec2_client = EC2Client()

            await ec2_client.detect_objects(image_url, result_upload_url, metadata)

            call_args = mock_make_request.call_args
            actual_payload = call_args[0][1]

            assert actual_payload["image_url"] == image_url
            assert actual_payload["result_upload_url"] == result_upload_url
            assert actual_payload["metadata"] == metadata

    @pytest.mark.asyncio
    async def test_payload_construction_process_combined(self):
        image_url = "https://test-bucket.s3.amazonaws.com/combined-test.jpg"
        result_upload_url = "https://result-bucket.s3.amazonaws.com/combined-result.json"
        maturation_threshold = 0.85
        metadata = {"analysis_type": "premium", "priority": "high"}

        with patch.object(EC2Client, "_make_request", new_callable=AsyncMock) as mock_make_request:
            mock_make_request.return_value = {"status": "success"}
            ec2_client = EC2Client()

            await ec2_client.process_combined(image_url, result_upload_url, maturation_threshold, metadata)

            call_args = mock_make_request.call_args
            actual_payload = call_args[0][1]

            assert actual_payload["image_url"] == image_url
            assert actual_payload["result_upload_url"] == result_upload_url
            assert actual_payload["maturation_threshold"] == maturation_threshold
            assert actual_payload["metadata"] == metadata
