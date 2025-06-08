from src.shared.domain.entities.combined_result import CombinedResult
from src.shared.domain.models.base_models import MaturationInfo
from src.shared.domain.models.combined_models import (
    CombinedContractResponse,
    ContractDetection,
    ContractDetectionResult,
    ContractDetectionSummary,
    ProcessingMetadata,
)


class ContractResponseMapper:
    @staticmethod
    def to_contract_response(combined_result: CombinedResult) -> CombinedContractResponse:

        detection_result = combined_result.detection_result

        contract_results = []
        for result in detection_result.results:
            maturation_info = None
            if result.maturation_level:
                maturation_info = MaturationInfo(
                    level=result.maturation_level.get("level", "unknown"),
                    confidence=result.maturation_level.get("confidence", 0.0),
                    stage=result.maturation_level.get("stage", "unknown"),
                )

            contract_result = ContractDetectionResult(
                class_name=result.class_name,
                confidence=result.confidence,
                bounding_box=result.bounding_box,
                maturation_level=maturation_info,
            )
            contract_results.append(contract_result)

        detection_summary = ContractDetectionSummary(
            total_detections=len(contract_results),
            detection_time_ms=detection_result.summary.get("detection_time_ms", 0),
            confidence_threshold=detection_result.summary.get("confidence_threshold", 0.6),
            classes_detected=list(set(r.class_name for r in contract_results)),
            average_confidence=(
                sum(r.confidence for r in contract_results) / len(contract_results) if contract_results else 0.0
            ),
        )

        contract_detection = ContractDetection(results=contract_results, summary=detection_summary)

        processing_metadata = ProcessingMetadata(
            model_version=detection_result.summary.get("model_version", "1.0"),
            processing_node=detection_result.summary.get("processing_node", "unknown"),
            image_dimensions=detection_result.summary.get("image_dimensions", {}),
            preprocessing_applied=detection_result.summary.get("preprocessing_applied", []),
        )

        return CombinedContractResponse(
            status=detection_result.status,
            request_id=detection_result.request_id,
            detection=contract_detection,
            image_result_url=detection_result.image_result_url,
            processing_time_ms=combined_result.total_processing_time_ms,
            processing_metadata=processing_metadata,
        )
