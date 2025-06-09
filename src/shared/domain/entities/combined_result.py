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

    def to_contract_dict(self) -> Dict[str, Any]:
        base = {
            "status": self.status,
            "request_id": self.request_id,
            "detection": self.detection.model_dump() if self.detection else {"results": [], "summary": {}},
            "image_result_url": self.image_result_url,
            "processing_time_ms": self.processing_time_ms,
        }
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
        )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CombinedResult":
        detection_data = data.get("detection_result", {})
        detection = None
        if detection_data and detection_data.get("summary"):
            summary_data = detection_data.get("summary", {})
            if "model_versions" not in summary_data:
                summary_data["model_versions"] = {}
            summary = ContractDetectionSummary(**summary_data)
            
            results_data = detection_data.get("results", [])
            results = [ContractDetectionResult(**res) for res in results_data]
            detection = ContractDetection(results=results, summary=summary)
        
        processing_metadata_data = data.get("processing_metadata")
        processing_metadata = ProcessingMetadata(**processing_metadata_data) if processing_metadata_data else None

        return cls(
            status=data.get("status", "unknown"),
            request_id=data.get("request_id"),
            detection=detection,
            image_result_url=data.get("image_result_url"),
            processing_time_ms=data.get("processing_time_ms", 0),
            processing_metadata=processing_metadata,
            error_code=data.get("error_info", {}).get("error_code"),
            error_message=data.get("error_info", {}).get("error_message"),
            error_details=data.get("error_info", {}).get("error_details"),
        )