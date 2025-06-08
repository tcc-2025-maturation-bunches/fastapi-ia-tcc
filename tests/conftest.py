import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.app.main import app
from src.shared.domain.entities.combined_result import CombinedResult
from src.shared.domain.entities.image import Image
from src.shared.domain.entities.result import DetectionResult, ProcessingResult
from src.shared.domain.enums.ia_model_type_enum import ModelType
from src.shared.domain.models.base_models import ProcessingMetadata
from src.shared.domain.models.combined_models import (
    ContractDetection,
    ContractDetectionResult,
    ContractDetectionSummary,
)

load_dotenv(".env.test")


@pytest.fixture(scope="session")
def client():
    """Fixture para o cliente de teste da API FastAPI."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def mock_s3_client():
    """Mock para o S3Client de baixo nível, usado nos testes unitários do S3Repository."""
    with patch("src.shared.infra.external.s3.s3_client.S3Client") as mock:
        s3_client_instance = mock.return_value
        s3_client_instance.generate_presigned_url = AsyncMock(
            return_value={"upload_url": "http://s3-upload.url", "key": "key", "expires_in_seconds": 900}
        )
        s3_client_instance.upload_file = AsyncMock(return_value="http://s3-file-url")
        s3_client_instance.get_file_url = AsyncMock(return_value="http://s3-file-url")
        s3_client_instance.delete_file = AsyncMock(return_value=True)
        yield s3_client_instance


@pytest.fixture
def mock_dynamo_client():
    """Mock para o DynamoClient de baixo nível, usado nos testes unitários do DynamoRepository."""
    with patch("src.shared.infra.external.dynamo.dynamo_client.DynamoClient") as mock:
        dynamo_client_instance = mock.return_value
        dynamo_client_instance.put_item = AsyncMock(return_value={"pk": "IMG#test-id", "sk": "META#test-id"})
        dynamo_client_instance.get_item = AsyncMock(return_value={"image_id": "test-id"})
        dynamo_client_instance.query_items = AsyncMock(return_value=[{"request_id": "test-req-id"}])
        dynamo_client_instance.convert_from_dynamo_item = MagicMock(side_effect=lambda x: x)
        yield dynamo_client_instance


@pytest.fixture
def sample_ec2_combined_response():
    """Fornece uma resposta mockada do serviço de IA (EC2), baseada no contrato de sucesso."""
    return {
        "status": "success",
        "request_id": "req-combined-9b2f4e",
        "detection": {
            "results": [
                {
                    "class_name": "banana",
                    "confidence": 0.95,
                    "bounding_box": [0.1, 0.1, 0.2, 0.2],
                    "maturation_level": {
                        "score": 0.75,
                        "category": "semi-ripe",
                        "estimated_days_until_spoilage": 5,
                        "color_analysis": {"green_ratio": 0.35, "yellow_ratio": 0.55, "brown_ratio": 0.10},
                    },
                }
            ],
            "summary": {
                "total_objects": 1,
                "objects_with_maturation": 1,
                "detection_time_ms": 320,
                "maturation_time_ms": 180,
                "average_maturation_score": 0.75,
                "model_versions": {"detection": "yolov8-fruit-v2.1", "maturation": "maturation-resnet50-v1.5"},
            },
        },
        "image_result_url": "https://bucket.s3.amazonaws.com/results/fruit_result.jpg",
        "processing_time_ms": 500,
        "processing_metadata": {
            "image_dimensions": {"width": 1920, "height": 1080},
            "maturation_distribution": {"verde": 0, "madura": 1, "passada": 0, "nao_analisado": 0},
            "preprocessing_time_ms": 45,
        },
    }


@pytest.fixture
def sample_combined_result_entity(sample_ec2_combined_response):
    """Cria uma instância da entidade CombinedResult a partir da resposta mockada do EC2."""
    data = sample_ec2_combined_response
    detection_data = data["detection"]
    summary_data = detection_data["summary"]
    metadata_data = data["processing_metadata"]
    results = [ContractDetectionResult(**res) for res in detection_data["results"]]
    summary = ContractDetectionSummary(**summary_data)
    detection = ContractDetection(results=results, summary=summary)
    processing_metadata = ProcessingMetadata(**metadata_data)

    return CombinedResult(
        status=data["status"],
        request_id=data["request_id"],
        detection=detection,
        image_result_url=data["image_result_url"],
        processing_time_ms=data["processing_time_ms"],
        processing_metadata=processing_metadata,
    )


@pytest.fixture
def sample_processing_result_combined(sample_ec2_combined_response):
    """Cria uma instância da entidade ProcessingResult para testes de endpoints legados."""
    detection_data = sample_ec2_combined_response["detection"]
    results = [DetectionResult.from_dict(res) for res in detection_data["results"]]

    return ProcessingResult(
        image_id="img-456",
        model_type=ModelType.COMBINED,
        results=results,
        status=sample_ec2_combined_response["status"],
        request_id=sample_ec2_combined_response["request_id"],
        summary=detection_data["summary"],
        image_result_url=sample_ec2_combined_response["image_result_url"],
    )


@pytest.fixture
def mock_ec2_client(sample_ec2_combined_response):
    """Mock para o EC2Client focado no método process_combined."""
    with patch("src.shared.infra.external.ec2.ec2_client.EC2Client") as mock:
        ec2_client_instance = mock.return_value
        ec2_client_instance.process_combined = AsyncMock(return_value=sample_ec2_combined_response)
        yield ec2_client_instance


@pytest.fixture
def mock_ia_repository(sample_combined_result_entity):
    """Mock para o IARepository focado no método process_combined."""
    with patch("src.modules.ia_integration.repo.ia_repository.IARepository") as mock:
        ia_repo_instance = mock.return_value
        ia_repo_instance.process_combined = AsyncMock(return_value=sample_combined_result_entity)
        yield ia_repo_instance


@pytest.fixture
def mock_s3_repository():
    """Mock para o S3Repository, usado em testes de use cases."""
    with patch("src.modules.storage.repo.s3_repository.S3Repository") as mock:
        s3_repo_instance = mock.return_value
        s3_repo_instance.generate_image_key = AsyncMock(return_value="test-user/image.jpg")
        s3_repo_instance.generate_presigned_url = AsyncMock(
            return_value={"upload_url": "http://s3-upload.url", "image_id": "id-123", "expires_in_seconds": 900}
        )
        s3_repo_instance.upload_file = AsyncMock(return_value="http://s3-file-url")
        s3_repo_instance.upload_image = AsyncMock(
            return_value=Image(image_id="id-456", image_url="http://image.url", user_id="user1")
        )
        s3_repo_instance.generate_result_key = AsyncMock(return_value="test-user/result.jpg")
        s3_repo_instance.generate_result_presigned_url = AsyncMock(
            return_value={"upload_url": "http://s3-result-upload.url", "key": "key-result", "expires_in_seconds": 900}
        )
        yield s3_repo_instance


@pytest.fixture
def mock_dynamo_repository():
    """Mock para o DynamoRepository, usado em testes de use cases."""
    with patch("src.modules.storage.repo.dynamo_repository.DynamoRepository") as mock:
        dynamo_repo_instance = mock.return_value
        dynamo_repo_instance.save_item = AsyncMock(return_value={})
        dynamo_repo_instance.get_item = AsyncMock(return_value=None)
        dynamo_repo_instance.save_request_summary = AsyncMock(return_value={})
        dynamo_repo_instance.get_combined_result = AsyncMock(return_value=None)
        dynamo_repo_instance.save_image_metadata = AsyncMock(return_value={})
        dynamo_repo_instance.save_processing_result = AsyncMock(return_value={})
        yield dynamo_repo_instance


@pytest.fixture
def sample_upload_file():
    """Fixture para simular um arquivo de upload (UploadFile do FastAPI)."""
    from unittest.mock import MagicMock

    class MockFile:
        def __init__(self):
            self.file = MagicMock()
            self.file.read = MagicMock(return_value=b"test file content")
            self.filename = "test.jpg"
            self.content_type = "image/jpeg"

    return MockFile()
