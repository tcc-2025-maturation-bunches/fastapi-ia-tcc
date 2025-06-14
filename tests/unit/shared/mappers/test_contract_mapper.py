from src.shared.domain.entities.combined_result import CombinedResult
from src.shared.domain.models.base_models import (
    ImageDimensions,
    MaturationDistribution,
    MaturationInfo,
    ProcessingMetadata,
)
from src.shared.domain.models.combined_models import (
    ContractDetection,
    ContractDetectionResult,
    ContractDetectionSummary,
)
from src.shared.mappers.contract_mapper import ContractResponseMapper


class TestContractResponseMapper:
    def test_to_contract_response_with_full_data(self):
        detection_results = [
            ContractDetectionResult(
                class_name="banana",
                confidence=0.95,
                bounding_box=[0.1, 0.2, 0.3, 0.4],
                maturation_level=MaturationInfo(score=0.75, category="semi-ripe", estimated_days_until_spoilage=5),
            ),
            ContractDetectionResult(
                class_name="apple", confidence=0.88, bounding_box=[0.5, 0.6, 0.2, 0.3], maturation_level=None
            ),
        ]

        detection_summary = ContractDetectionSummary(
            total_objects=2,
            objects_with_maturation=1,
            detection_time_ms=150,
            maturation_time_ms=200,
            average_maturation_score=0.75,
            model_versions=None,
        )

        detection = ContractDetection(results=detection_results, summary=detection_summary)

        processing_metadata = ProcessingMetadata(
            image_dimensions=ImageDimensions(width=1920, height=1080),
            maturation_distribution=MaturationDistribution(verde=0, madura=1, passada=0, nao_analisado=1),
        )

        combined_result = CombinedResult(
            status="success",
            request_id="req-test-123",
            detection=detection,
            image_result_url="https://example.com/result.jpg",
            processing_time_ms=500,
            processing_metadata=processing_metadata,
        )

        contract_response = ContractResponseMapper.to_contract_response(combined_result)

        assert contract_response.status == "success"
        assert contract_response.request_id == "req-test-123"
        assert contract_response.image_result_url == "https://example.com/result.jpg"
        assert contract_response.processing_time_ms == 500
        assert contract_response.processing_metadata == processing_metadata
        assert len(contract_response.detection.results) == 2

        first_result = contract_response.detection.results[0]
        assert first_result.class_name == "banana"
        assert first_result.confidence == 0.95
        assert first_result.bounding_box == [0.1, 0.2, 0.3, 0.4]
        assert first_result.maturation_level is not None
        assert first_result.maturation_level.score == 0.75
        assert first_result.maturation_level.category == "semi-ripe"
        assert first_result.maturation_level.estimated_days_until_spoilage == 5

        second_result = contract_response.detection.results[1]
        assert second_result.class_name == "apple"
        assert second_result.confidence == 0.88
        assert second_result.maturation_level is None

        assert contract_response.detection.summary.total_objects == 2
        assert contract_response.detection.summary.objects_with_maturation == 1

    def test_to_contract_response_with_no_detection(self):
        combined_result = CombinedResult(
            status="error",
            request_id="req-error-456",
            detection=None,
            image_result_url=None,
            processing_time_ms=0,
            processing_metadata=None,
        )

        contract_response = ContractResponseMapper.to_contract_response(combined_result)
        print(contract_response)
        assert contract_response.status == "error"
        assert contract_response.request_id == "req-error-456"
        assert contract_response.image_result_url is None
        assert contract_response.processing_time_ms == 0

        assert contract_response.detection is not None
        assert len(contract_response.detection.results) == 0
        assert contract_response.detection.summary.total_objects == 0
        assert contract_response.detection.summary.objects_with_maturation == 0

    def test_to_contract_response_with_maturation_dict(self):
        detection_result = ContractDetectionResult(
            class_name="orange",
            confidence=0.92,
            bounding_box=[0.2, 0.3, 0.4, 0.5],
            maturation_level=MaturationInfo(score=0.8, category="ripe", estimated_days_until_spoilage=3),
        )

        detection = ContractDetection(
            results=[detection_result],
            summary=ContractDetectionSummary(
                total_objects=1,
                objects_with_maturation=1,
                detection_time_ms=100,
                maturation_time_ms=150,
                average_maturation_score=0.8,
                model_versions=None,
            ),
        )

        combined_result = CombinedResult(
            status="success",
            request_id="req-dict-test",
            detection=detection,
            image_result_url="https://example.com/orange.jpg",
            processing_time_ms=300,
            processing_metadata=None,
        )

        contract_response = ContractResponseMapper.to_contract_response(combined_result)

        assert len(contract_response.detection.results) == 1
        result = contract_response.detection.results[0]
        assert result.class_name == "orange"
        assert result.maturation_level is not None
        assert result.maturation_level.score == 0.8
        assert result.maturation_level.category == "ripe"

    def test_to_contract_response_with_object_maturation_level(self):
        detection_result = ContractDetectionResult(
            class_name="avocado",
            confidence=0.87,
            bounding_box=[0.1, 0.1, 0.5, 0.6],
            maturation_level=MaturationInfo(score=0.65, category="green", estimated_days_until_spoilage=7),
        )

        detection = ContractDetection(
            results=[detection_result],
            summary=ContractDetectionSummary(
                total_objects=1,
                objects_with_maturation=1,
                detection_time_ms=120,
                maturation_time_ms=180,
                average_maturation_score=0.65,
                model_versions=None,
            ),
        )

        combined_result = CombinedResult(
            status="success",
            request_id="req-obj-test",
            detection=detection,
            image_result_url="https://example.com/avocado.jpg",
            processing_time_ms=350,
            processing_metadata=None,
        )

        contract_response = ContractResponseMapper.to_contract_response(combined_result)

        assert len(contract_response.detection.results) == 1
        result = contract_response.detection.results[0]
        assert result.class_name == "avocado"
        assert result.maturation_level is not None
        assert result.maturation_level.score == 0.65
        assert result.maturation_level.category == "green"
        assert result.maturation_level.estimated_days_until_spoilage == 7

    def test_to_contract_response_with_no_summary(self):
        detection_results = [
            ContractDetectionResult(
                class_name="grape",
                confidence=0.78,
                bounding_box=[0.3, 0.4, 0.2, 0.3],
                maturation_level=MaturationInfo(score=0.9, category="ripe"),
            )
        ]

        detection = ContractDetection(
            results=detection_results,
            summary=ContractDetectionSummary(
                total_objects=1,
                objects_with_maturation=1,
                detection_time_ms=0,
                maturation_time_ms=0,
                average_maturation_score=0.9,
                model_versions=None,
            ),
        )

        combined_result = CombinedResult(
            status="success",
            request_id="req-no-summary",
            detection=detection,
            image_result_url="https://example.com/grape.jpg",
            processing_time_ms=250,
            processing_metadata=None,
        )

        contract_response = ContractResponseMapper.to_contract_response(combined_result)

        assert contract_response.detection.summary is not None
        assert contract_response.detection.summary.total_objects == 1
        assert contract_response.detection.summary.objects_with_maturation == 1
        assert contract_response.detection.summary.average_maturation_score == 0.9

    def test_to_contract_response_with_mixed_maturation_data(self):
        detection_results = [
            ContractDetectionResult(
                class_name="strawberry",
                confidence=0.93,
                bounding_box=[0.1, 0.2, 0.3, 0.4],
                maturation_level=MaturationInfo(score=0.85, category="ripe"),
            ),
            ContractDetectionResult(
                class_name="pineapple", confidence=0.91, bounding_box=[0.5, 0.6, 0.3, 0.4], maturation_level=None
            ),
            ContractDetectionResult(
                class_name="mango",
                confidence=0.89,
                bounding_box=[0.2, 0.8, 0.2, 0.3],
                maturation_level=MaturationInfo(score=0.65, category="unripe"),
            ),
        ]

        detection = ContractDetection(
            results=detection_results,
            summary=ContractDetectionSummary(
                total_objects=3,
                objects_with_maturation=2,
                detection_time_ms=0,
                maturation_time_ms=0,
                average_maturation_score=0.75,
                model_versions=None,
            ),
        )

        combined_result = CombinedResult(
            status="success",
            request_id="req-mixed-test",
            detection=detection,
            image_result_url="https://example.com/fruits.jpg",
            processing_time_ms=400,
            processing_metadata=None,
        )

        contract_response = ContractResponseMapper.to_contract_response(combined_result)

        assert contract_response.detection.summary.total_objects == 3
        assert contract_response.detection.summary.objects_with_maturation == 2
        assert contract_response.detection.summary.average_maturation_score == 0.75

    def test_to_contract_response_empty_results(self):
        detection = ContractDetection(
            results=[],
            summary=ContractDetectionSummary(
                total_objects=0,
                objects_with_maturation=0,
                detection_time_ms=50,
                maturation_time_ms=0,
                average_maturation_score=0.0,
                model_versions=None,
            ),
        )

        combined_result = CombinedResult(
            status="success",
            request_id="req-empty-results",
            detection=detection,
            image_result_url="https://example.com/empty.jpg",
            processing_time_ms=100,
            processing_metadata=None,
        )

        contract_response = ContractResponseMapper.to_contract_response(combined_result)

        assert len(contract_response.detection.results) == 0
        assert contract_response.detection.summary.total_objects == 0
        assert contract_response.detection.summary.objects_with_maturation == 0
        assert contract_response.detection.summary.average_maturation_score == 0.0
