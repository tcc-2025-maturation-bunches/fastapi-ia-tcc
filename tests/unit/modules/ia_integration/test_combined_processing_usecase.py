import uuid
from unittest.mock import AsyncMock

import pytest

from src.modules.ia_integration.usecase.combined_processing_usecase import CombinedProcessingUseCase


class TestCombinedProcessingUseCaseRefactored:

    @pytest.mark.asyncio
    async def test_start_processing_creates_queued_status(self, mock_dynamo_repository):
        """
        Testa se o método start_processing cria um registro de status 'queued' no DynamoDB.
        """
        usecase = CombinedProcessingUseCase(dynamo_repository=mock_dynamo_repository)
        request_id = await usecase.start_processing(
            image_url="http://image.url/test.jpg",
            user_id="test_user",
            metadata={"image_id": "test_img_1", "location": "loc_A"},
            maturation_threshold=0.7,
        )

        assert request_id.startswith("req-combined-")

        mock_dynamo_repository.save_request_summary.assert_called_once()
        call_args = mock_dynamo_repository.save_request_summary.call_args[0]
        assert call_args[0] == "processing_status"
        saved_data = call_args[1]
        assert saved_data["pk"] == f"PROCESSING#{request_id}"
        assert saved_data["status"] == "queued"
        assert saved_data["progress"] == 0.0
        assert saved_data["image_id"] == "test_img_1"

    @pytest.mark.asyncio
    async def test_execute_in_background_success_flow(
        self, mock_ia_repository, mock_dynamo_repository, mock_s3_repository, sample_combined_result_entity
    ):
        """
        Testa o fluxo de sucesso completo do processamento em background.
        """
        request_id = f"req-combined-{uuid.uuid4().hex[:8]}"
        initial_status = {
            "pk": f"PROCESSING#{request_id}",
            "sk": "STATUS",
            "status": "queued",
            "image_url": "http://image.url/test.jpg",
            "user_id": "test_user",
            "image_id": "test_img_1",
            "location": "loc_A",
        }

        mock_dynamo_repository.get_item = AsyncMock(return_value=initial_status)
        mock_ia_repository.process_combined = AsyncMock(return_value=sample_combined_result_entity)

        usecase = CombinedProcessingUseCase(
            ia_repository=mock_ia_repository, dynamo_repository=mock_dynamo_repository, s3_repository=mock_s3_repository
        )

        await usecase.execute_in_background(
            request_id=request_id,
            image_url=initial_status["image_url"],
            user_id=initial_status["user_id"],
            metadata={"image_id": initial_status["image_id"], "location": initial_status["location"]},
        )

        mock_ia_repository.process_combined.assert_called_once()
        mock_dynamo_repository.save_request_summary.assert_called_once()
        summary_call = mock_dynamo_repository.save_request_summary.call_args[0][0]
        assert summary_call["status"] == "success"
        assert summary_call["request_id"] == request_id

        final_status_call = mock_dynamo_repository.save_request_summary.call_args[0][1]
        assert final_status_call["status"] == "completed"
        assert final_status_call["progress"] == 1.0
