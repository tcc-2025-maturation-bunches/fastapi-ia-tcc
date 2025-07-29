from typing import Any, Dict, Optional
from uuid import uuid4

from src.shared.domain.models.combined_models import (
    ContractDetection,
    ContractDetectionResult,
    ContractDetectionSummary,
    ProcessingMetadata,
)


class CombinedResult:

    def __init__(
        self,
        status: str,
        request_id: Optional[str] = None,
        detection: Optional[ContractDetection] = None,
        image_result_url: Optional[str] = None,
        processing_time_ms: int = 0,
        processing_metadata: Optional[ProcessingMetadata] = None,
        error_code: Optional[str] = None,
        error_message: Optional[str] = None,
        error_details: Optional[Dict[str, Any]] = None,
        image_id: Optional[str] = None,
        user_id: Optional[str] = None,
        image_url: Optional[str] = None,
        **kwargs,
    ):
        self.status = status
        self.request_id = request_id or f"req-combined-{uuid4().hex[:8]}"
        self.detection = detection
        self.image_result_url = image_result_url
        self.processing_time_ms = processing_time_ms
        self.processing_metadata = processing_metadata
        self.error_code = error_code
        self.error_message = error_message
        self.error_details = error_details
        self.image_id = image_id
        self.user_id = user_id
        self.image_url = image_url
        self.extra_fields = kwargs

    def to_contract_dict(self) -> Dict[str, Any]:
        base = {
            "status": self.status,
            "request_id": self.request_id,
            "detection": self.detection.model_dump() if self.detection else {"results": [], "summary": {}},
            "image_result_url": self.image_result_url,
            "processing_time_ms": self.processing_time_ms,
        }

        if self.image_id:
            base["image_id"] = self.image_id
        if self.user_id:
            base["user_id"] = self.user_id
        if self.image_url:
            base["image_url"] = self.image_url

        if self.processing_metadata is not None:
            base["processing_metadata"] = self.processing_metadata.model_dump()

        if self.status in ("error", "partial_error"):
            if self.error_code is not None:
                base["error_code"] = self.error_code
            if self.error_message is not None:
                base["error_message"] = self.error_message
            if self.error_details is not None:
                base["error_details"] = self.error_details

        return base

    @classmethod
    def from_domain(
        cls,
        status: str,
        detection_results: list,
        summary: ContractDetectionSummary,
        image_result_url: Optional[str],
        processing_time_ms: int,
        processing_metadata: Optional[ProcessingMetadata],
        request_id: Optional[str] = None,
        error_code: Optional[str] = None,
        error_message: Optional[str] = None,
        error_details: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> "CombinedResult":
        detection = ContractDetection(
            results=[
                ContractDetectionResult(**r) if not isinstance(r, ContractDetectionResult) else r
                for r in detection_results
            ],
            summary=summary,
        )
        return cls(
            status=status,
            request_id=request_id,
            detection=detection,
            image_result_url=image_result_url,
            processing_time_ms=processing_time_ms,
            processing_metadata=processing_metadata,
            error_code=error_code,
            error_message=error_message,
            error_details=error_details,
            **kwargs,
        )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CombinedResult":
        detection_data = data.get("detection_result", {})
        detection = None

        if detection_data and detection_data.get("summary"):
            summary_data = detection_data.get("summary", {})

            def safe_int(value, default=0):
                try:
                    return int(value) if value is not None else default
                except (ValueError, TypeError):
                    return default

            def safe_float(value, default=0.0):
                try:
                    return float(value) if value is not None else default
                except (ValueError, TypeError):
                    return default

            model_versions = summary_data.get("model_versions", {})
            if not isinstance(model_versions, dict):
                model_versions = {"detection": "unknown", "maturation": "unknown"}

            summary = ContractDetectionSummary(
                total_objects=safe_int(summary_data.get("total_objects")),
                objects_with_maturation=safe_int(summary_data.get("objects_with_maturation")),
                detection_time_ms=safe_int(summary_data.get("detection_time_ms")),
                maturation_time_ms=safe_int(summary_data.get("maturation_time_ms")),
                average_maturation_score=safe_float(summary_data.get("average_maturation_score")),
                model_versions=model_versions,
            )

            results_data = detection_data.get("results", [])
            results = []

            for res in results_data:
                confidence = safe_float(res.get("confidence"))

                bbox = res.get("bounding_box", [])
                if isinstance(bbox, list) and all(isinstance(x, str) for x in bbox):
                    bbox = [safe_float(x) for x in bbox]

                maturation_data = res.get("maturation_level")
                maturation_level = None
                if maturation_data:
                    from src.shared.domain.models.base_models import MaturationInfo

                    maturation_level = MaturationInfo(
                        score=safe_float(maturation_data.get("score", 0)),
                        category=maturation_data.get("category", "unknown"),
                    )

                result = ContractDetectionResult(
                    class_name=res.get("class_name", "unknown"),
                    confidence=confidence,
                    bounding_box=bbox,
                    maturation_level=maturation_level,
                )
                results.append(result)

            detection = ContractDetection(results=results, summary=summary)

        processing_metadata_data = data.get("processing_metadata")
        processing_metadata = None

        if processing_metadata_data:
            image_dimensions = processing_metadata_data.get("image_dimensions", {})
            if image_dimensions:
                image_dimensions = {
                    "width": int(image_dimensions.get("width", 0)),
                    "height": int(image_dimensions.get("height", 0)),
                }

            maturation_dist = processing_metadata_data.get("maturation_distribution", {})
            if maturation_dist:
                maturation_dist = {k: int(v) if isinstance(v, str) else v for k, v in maturation_dist.items()}

            from src.shared.domain.models.base_models import ImageDimensions, MaturationDistribution

            processing_metadata = ProcessingMetadata(
                image_dimensions=ImageDimensions(**image_dimensions) if image_dimensions else None,
                maturation_distribution=MaturationDistribution(**maturation_dist) if maturation_dist else None,
            )

        processing_time_ms = data.get("processing_time_ms", 0)
        if isinstance(processing_time_ms, str):
            try:
                processing_time_ms = int(processing_time_ms)
            except (ValueError, TypeError):
                processing_time_ms = 0

        error_info = data.get("error_info", {}) or {}

        return cls(
            status=data.get("status", "unknown"),
            request_id=data.get("request_id"),
            detection=detection,
            image_result_url=data.get("image_result_url"),
            processing_time_ms=processing_time_ms,
            processing_metadata=processing_metadata,
            error_code=error_info.get("error_code"),
            error_message=error_info.get("error_message"),
            error_details=error_info.get("error_details"),
            image_id=data.get("image_id"),
            user_id=data.get("user_id"),
            image_url=data.get("image_url"),
            pk=data.get("pk"),
            sk=data.get("sk"),
            createdAt=data.get("createdAt"),
            updatedAt=data.get("updatedAt"),
            initial_metadata=data.get("initial_metadata"),
            additional_metadata=data.get("additional_metadata"),
        )
