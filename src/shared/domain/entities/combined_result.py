from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from src.shared.domain.entities.result import DetectionResult, ProcessingResult
from src.shared.domain.enums.ia_model_type_enum import ModelType


class CombinedResult:
    """Classe que representa um resultado combinado de detecção e maturação."""

    def __init__(
        self,
        image_id: str,
        user_id: str,
        detection_result: ProcessingResult,
        maturation_result: Optional[ProcessingResult] = None,
        location: Optional[str] = None,
        processing_timestamp: Optional[datetime] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        combined_id: Optional[str] = None,
    ):
        self.image_id = image_id
        self.user_id = user_id
        self.detection_result = detection_result
        self.maturation_result = maturation_result
        self.location = location
        self.processing_timestamp = processing_timestamp or datetime.now(timezone.utc)
        self.created_at = created_at or datetime.now(timezone.utc)
        self.updated_at = updated_at or datetime.now(timezone.utc)
        self.combined_id = combined_id or f"combined-{uuid4()}"

        if detection_result and detection_result.status == "success":
            if detection_result.model_type == ModelType.COMBINED:
                self.status = "completed"
            else:
                self.status = "detection_completed"
        else:
            self.status = "error"

        self.total_processing_time_ms = self._calculate_total_processing_time()
        self.results = self._merge_results()

    def _calculate_total_processing_time(self) -> int:
        """Calcula o tempo total de processamento."""
        if self.detection_result.model_type == ModelType.COMBINED:
            return self.detection_result.summary.get(
                "total_processing_time_ms", 0
            ) or self.detection_result.summary.get("detection_time_ms", 0)

        detection_time = self.detection_result.summary.get("detection_time_ms", 0)
        maturation_time = 0
        if self.maturation_result:
            maturation_time = self.maturation_result.summary.get("detection_time_ms", 0)
        return detection_time + maturation_time

    def _merge_results(self) -> List[Dict[str, Any]]:
        """Mescla os resultados de detecção e maturação."""
        if self.detection_result.model_type == ModelType.COMBINED:
            return [r.to_dict() for r in self.detection_result.results]

    def to_dict(self) -> Dict[str, Any]:
        """Converte a entidade para dicionário."""
        result = {
            "pk": f"IMG#{self.image_id}",
            "sk": "RESULT#COMBINED",
            "entity_type": "COMBINED_RESULT",
            "combined_id": self.combined_id,
            "image_id": self.image_id,
            "user_id": self.user_id,
            "processing_timestamp": self.processing_timestamp.isoformat(),
            "detection": {
                "request_id": self.detection_result.request_id,
                "status": self.detection_result.status,
                "processing_timestamp": self.detection_result.processing_timestamp.isoformat(),
                "summary": self.detection_result.summary,
                "image_result_url": self.detection_result.image_result_url,
                "model_type": self.detection_result.model_type.value,
            },
            "results": self.results,
            "total_processing_time_ms": self.total_processing_time_ms,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

        if self.location:
            result["location"] = self.location

        if self.maturation_result:
            result["maturation"] = {
                "request_id": self.maturation_result.request_id,
                "status": self.maturation_result.status,
                "processing_timestamp": self.maturation_result.processing_timestamp.isoformat(),
                "summary": self.maturation_result.summary,
                "image_result_url": self.maturation_result.image_result_url,
            }

        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CombinedResult":
        """Cria uma instância a partir de um dicionário."""
        processing_timestamp = None
        if data.get("processing_timestamp"):
            processing_timestamp = datetime.fromisoformat(data["processing_timestamp"])

        created_at = None
        if data.get("created_at"):
            created_at = datetime.fromisoformat(data["created_at"])

        updated_at = None
        if data.get("updated_at"):
            updated_at = datetime.fromisoformat(data["updated_at"])

        detection_data = data.get("detection", {})
        detection_result = None
        if detection_data:
            detection_timestamp = None
            if detection_data.get("processing_timestamp"):
                detection_timestamp = datetime.fromisoformat(detection_data["processing_timestamp"])

            detection_results = []
            for result_data in detection_data.get("results", []):
                detection_result_obj = DetectionResult.from_dict(result_data)
                detection_results.append(detection_result_obj)

            model_type_str = detection_data.get("model_type", "detection")
            try:
                model_type = ModelType(model_type_str)
            except ValueError:
                model_type = ModelType.DETECTION

            detection_result = ProcessingResult(
                image_id=data["image_id"],
                model_type=model_type,
                results=detection_results,
                status=detection_data.get("status", "error"),
                request_id=detection_data.get("request_id"),
                processing_timestamp=detection_timestamp,
                summary=detection_data.get("summary", {}),
                image_result_url=detection_data.get("image_result_url"),
            )

        maturation_data = data.get("maturation")
        maturation_result = None
        if maturation_data:
            maturation_timestamp = None
            if maturation_data.get("processing_timestamp"):
                maturation_timestamp = datetime.fromisoformat(maturation_data["processing_timestamp"])

            maturation_results = []
            for result_data in maturation_data.get("results", []):
                maturation_result_obj = DetectionResult.from_dict(result_data)
                maturation_results.append(maturation_result_obj)

            maturation_result = ProcessingResult(
                image_id=data["image_id"],
                model_type=ModelType.MATURATION,
                results=maturation_results,
                status=maturation_data.get("status", "error"),
                request_id=maturation_data.get("request_id"),
                processing_timestamp=maturation_timestamp,
                summary=maturation_data.get("summary", {}),
                image_result_url=maturation_data.get("image_result_url"),
            )

        return cls(
            image_id=data["image_id"],
            user_id=data["user_id"],
            detection_result=detection_result,
            maturation_result=maturation_result,
            location=data.get("location"),
            processing_timestamp=processing_timestamp,
            created_at=created_at,
            updated_at=updated_at,
            combined_id=data.get("combined_id"),
        )
