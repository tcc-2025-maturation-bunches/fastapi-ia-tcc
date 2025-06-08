from datetime import datetime

from src.shared.domain.entities.result import DetectionResult, ProcessingResult
from src.shared.domain.enums.ia_model_type_enum import ModelType


class TestDetectionResultEntity:
    def test_detection_result_creation(self):
        class_name = "banana"
        confidence = 0.96
        bounding_box = [0.1, 0.2, 0.3, 0.4]

        detection = DetectionResult(class_name=class_name, confidence=confidence, bounding_box=bounding_box)

        assert detection.class_name == class_name
        assert detection.confidence == confidence
        assert detection.bounding_box == bounding_box
        assert detection.maturation_level is None

    def test_detection_result_with_maturation(self):
        class_name = "banana"
        confidence = 0.97
        bounding_box = [0.15, 0.25, 0.35, 0.45]
        maturation_level = {
            "score": 0.75,
            "category": "semi-ripe",
            "estimated_days_until_spoilage": 5,
        }

        detection = DetectionResult(
            class_name=class_name,
            confidence=confidence,
            bounding_box=bounding_box,
            maturation_level=maturation_level,
        )

        assert detection.class_name == class_name
        assert detection.confidence == confidence
        assert detection.bounding_box == bounding_box
        assert detection.maturation_level == maturation_level

    def test_detection_result_to_dict(self):
        detection = DetectionResult(
            class_name="banana",
            confidence=0.98,
            bounding_box=[0.12, 0.22, 0.32, 0.42],
            maturation_level={
                "score": 0.9,
                "category": "ripe",
                "estimated_days_until_spoilage": 2,
            },
        )

        detection_dict = detection.to_dict()

        assert detection_dict["class_name"] == "banana"
        assert detection_dict["confidence"] == 0.98
        assert detection_dict["bounding_box"] == [0.12, 0.22, 0.32, 0.42]
        assert detection_dict["maturation_level"]["score"] == 0.9
        assert detection_dict["maturation_level"]["category"] == "ripe"
        assert detection_dict["maturation_level"]["estimated_days_until_spoilage"] == 2

    def test_detection_result_from_dict(self):
        detection_dict = {
            "class_name": "banana",
            "confidence": 0.92,
            "bounding_box": [0.14, 0.24, 0.34, 0.44],
            "maturation_level": {
                "score": 0.3,
                "category": "unripe",
                "estimated_days_until_spoilage": 8,
            },
        }

        detection = DetectionResult.from_dict(detection_dict)

        assert detection.class_name == "banana"
        assert detection.confidence == 0.92
        assert detection.bounding_box == [0.14, 0.24, 0.34, 0.44]
        assert detection.maturation_level["score"] == 0.3
        assert detection.maturation_level["category"] == "unripe"
        assert detection.maturation_level["estimated_days_until_spoilage"] == 8


class TestProcessingResultEntity:
    def test_processing_result_creation(self):
        image_id = "banana-batch-123-img"
        model_type = ModelType.COMBINED
        results = [DetectionResult(class_name="banana", confidence=0.95, bounding_box=[0.1, 0.2, 0.3, 0.4])]

        processing_result = ProcessingResult(image_id=image_id, model_type=model_type, results=results)

        assert processing_result.image_id == image_id
        assert processing_result.model_type == model_type
        assert len(processing_result.results) == 1
        assert processing_result.status == "success"
        assert processing_result.request_id is not None
        assert isinstance(processing_result.processing_timestamp, datetime)
        assert isinstance(processing_result.summary, dict)
        assert processing_result.image_result_url is None
        assert processing_result.error_message is None

    def test_processing_result_with_custom_values(self):
        image_id = "banana-ripeness-check-456"
        model_type = ModelType.COMBINED
        results = [
            DetectionResult(
                class_name="banana",
                confidence=0.97,
                bounding_box=[0.15, 0.25, 0.35, 0.45],
                maturation_level={
                    "score": 0.8,
                    "category": "ripe",
                    "estimated_days_until_spoilage": 3,
                },
            )
        ]
        status = "error"
        request_id = "banana-maturation-req-789"
        timestamp = datetime(2025, 5, 12, 10, 30, 0)
        summary = {"maturation_analysis_time_ms": 420}
        image_result_url = "https://fruit-analysis.com/results/banana_maturation_result_789.jpg"
        error_message = "Pontos de maturação não detectáveis"

        processing_result = ProcessingResult(
            image_id=image_id,
            model_type=model_type,
            results=results,
            status=status,
            request_id=request_id,
            processing_timestamp=timestamp,
            summary=summary,
            image_result_url=image_result_url,
            error_message=error_message,
        )

        assert processing_result.image_id == image_id
        assert processing_result.model_type == model_type
        assert len(processing_result.results) == 1
        assert processing_result.status == status
        assert processing_result.request_id == request_id
        assert processing_result.processing_timestamp == timestamp
        assert processing_result.summary == summary
        assert processing_result.image_result_url == image_result_url
        assert processing_result.error_message == error_message

    def test_processing_result_to_dict(self):
        image_id = "banana-shipment-567"
        model_type = ModelType.COMBINED
        results = [
            DetectionResult(
                class_name="banana",
                confidence=0.99,
                bounding_box=[0.11, 0.21, 0.31, 0.41],
                maturation_level={
                    "score": 0.7,
                    "category": "semi-ripe",
                    "estimated_days_until_spoilage": 4,
                },
            )
        ]
        status = "success"
        request_id = "banana-maturation-analysis-321"
        timestamp = datetime(2025, 5, 12, 10, 30, 0)
        summary = {"maturation_pattern_analysis_ms": 380}
        image_result_url = "https://fruit-analysis.com/results/banana_maturation_567.jpg"

        processing_result = ProcessingResult(
            image_id=image_id,
            model_type=model_type,
            results=results,
            status=status,
            request_id=request_id,
            processing_timestamp=timestamp,
            summary=summary,
            image_result_url=image_result_url,
        )
        result_dict = processing_result.to_dict()

        assert result_dict["image_id"] == image_id
        assert result_dict["model_type"] == model_type.value
        assert len(result_dict["results"]) == 1
        assert result_dict["status"] == status
        assert result_dict["request_id"] == request_id
        assert result_dict["processing_timestamp"] == timestamp.isoformat()
        assert result_dict["summary"] == summary
        assert result_dict["image_result_url"] == image_result_url
        assert result_dict["error_message"] is None

    def test_processing_result_from_dict(self):
        result_dict = {
            "image_id": "banana-crate-inspection-654",
            "model_type": "combined",
            "results": [
                {
                    "class_name": "banana",
                    "confidence": 0.96,
                    "bounding_box": [0.13, 0.23, 0.33, 0.43],
                    "maturation_level": {
                        "score": 0.85,
                        "category": "ripe",
                        "estimated_days_until_spoilage": 2,
                    },
                }
            ],
            "status": "success",
            "request_id": "banana-ripeness-analysis-987",
            "processing_timestamp": "2025-05-12T10:30:00",
            "summary": {"maturation_points_identified": 12, "analysis_time_ms": 360},
            "image_result_url": "https://fruit-analysis.com/results/banana_ripeness_assessment_654.jpg",
        }

        processing_result = ProcessingResult.from_dict(result_dict)

        assert processing_result.image_id == "banana-crate-inspection-654"
        assert processing_result.model_type == ModelType.COMBINED
        assert len(processing_result.results) == 1
        assert processing_result.results[0].class_name == "banana"
        assert processing_result.results[0].confidence == 0.96
        assert processing_result.results[0].maturation_level["score"] == 0.85
        assert processing_result.status == "success"
        assert processing_result.request_id == "banana-ripeness-analysis-987"
        assert processing_result.processing_timestamp.isoformat() == "2025-05-12T10:30:00"
        assert processing_result.summary == {
            "maturation_points_identified": 12,
            "analysis_time_ms": 360,
        }
        assert (
            processing_result.image_result_url
            == "https://fruit-analysis.com/results/banana_ripeness_assessment_654.jpg"
        )
