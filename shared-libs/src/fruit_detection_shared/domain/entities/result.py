from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from src.domain.enums.ia_model_type_enum import ModelType


class DetectionResult:
    def __init__(
        self,
        class_name: str,
        confidence: float,
        bounding_box: List[float],
        maturation_level: Optional[Dict[str, Any]] = None,
    ):
        self.class_name = class_name
        self.confidence = confidence
        self.bounding_box = bounding_box
        self.maturation_level = maturation_level

    def to_dict(self) -> Dict[str, Any]:
        return {
            "class_name": self.class_name,
            "confidence": self.confidence,
            "bounding_box": self.bounding_box,
            "maturation_level": self.maturation_level,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DetectionResult":
        return cls(
            class_name=data["class_name"],
            confidence=data["confidence"],
            bounding_box=data["bounding_box"],
            maturation_level=data.get("maturation_level"),
        )


class ProcessingResult:
    def __init__(
        self,
        image_id: str,
        model_type: ModelType,
        results: List[DetectionResult],
        status: str = "success",
        request_id: Optional[str] = None,
        processing_timestamp: Optional[datetime] = None,
        summary: Optional[Dict[str, Any]] = None,
        image_result_url: Optional[str] = None,
        error_message: Optional[str] = None,
        parent_request_id: Optional[str] = None,
    ):
        self.request_id = request_id or f"req-{uuid4()}"
        self.image_id = image_id
        self.model_type = model_type
        self.results = results
        self.status = status
        self.processing_timestamp = processing_timestamp or datetime.now(timezone.utc)
        self.summary = summary or {}
        self.image_result_url = image_result_url
        self.error_message = error_message
        self.parent_request_id = parent_request_id

    def to_dict(self) -> Dict[str, Any]:
        result_dict = {
            "request_id": self.request_id,
            "image_id": self.image_id,
            "model_type": self.model_type.value,
            "results": [result.to_dict() for result in self.results],
            "status": self.status,
            "processing_timestamp": self.processing_timestamp.isoformat(),
            "summary": self.summary,
            "image_result_url": self.image_result_url,
            "error_message": self.error_message,
        }

        if self.parent_request_id:
            result_dict["parent_request_id"] = self.parent_request_id

        return result_dict

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProcessingResult":
        processing_timestamp = data.get("processing_timestamp")
        if processing_timestamp and isinstance(processing_timestamp, str):
            processing_timestamp = datetime.fromisoformat(processing_timestamp)

        results = [DetectionResult.from_dict(result_data) for result_data in data.get("results", [])]

        return cls(
            request_id=data.get("request_id"),
            image_id=data["image_id"],
            model_type=ModelType(data["model_type"]),
            results=results,
            status=data.get("status", "success"),
            processing_timestamp=processing_timestamp,
            summary=data.get("summary", {}),
            image_result_url=data.get("image_result_url"),
            error_message=data.get("error_message"),
            parent_request_id=data.get("parent_request_id"),
        )

    @classmethod
    def from_ec2_response(cls, response: Dict[str, Any], image_id: str, model_type: ModelType) -> "ProcessingResult":
        results = []
        for result_data in response.get("results", []):
            results.append(
                DetectionResult(
                    class_name=result_data["class_name"],
                    confidence=result_data["confidence"],
                    bounding_box=result_data["bounding_box"],
                    maturation_level=result_data.get("maturation_level"),
                )
            )

        return cls(
            image_id=image_id,
            model_type=model_type,
            results=results,
            status=response.get("status", "success"),
            request_id=response.get("request_id"),
            summary=response.get("summary", {}),
            image_result_url=response.get("image_result_url"),
            error_message=response.get("error_message"),
        )
