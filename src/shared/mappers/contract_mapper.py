from src.shared.domain.entities.combined_result import CombinedResult
from src.shared.domain.models.base_models import MaturationInfo
from src.shared.domain.models.combined_models import (
    CombinedContractResponse,
    ContractDetection,
    ContractDetectionResult,
    ContractDetectionSummary,
)


class ContractResponseMapper:
    @staticmethod
    def to_contract_response(combined_result: CombinedResult) -> CombinedContractResponse:
        detection_data = combined_result.detection

        if not detection_data:
            detection_data = ContractDetection(
                results=[],
                summary=ContractDetectionSummary(
                    total_objects=0,
                    objects_with_maturation=0,
                    detection_time_ms=0,
                    maturation_time_ms=0,
                    average_maturation_score=0.0,
                    model_versions=None,
                ),
            )

        contract_results = []
        if detection_data.results:
            for result in detection_data.results:
                maturation_info = None
                if hasattr(result, "maturation_level") and result.maturation_level:
                    if isinstance(result.maturation_level, MaturationInfo):
                        maturation_info = result.maturation_level
                    elif isinstance(result.maturation_level, dict):
                        maturation_info = MaturationInfo(
                            score=result.maturation_level.get("score", 0.0),
                            category=result.maturation_level.get("category", "unknown"),
                            estimated_days_until_spoilage=result.maturation_level.get("estimated_days_until_spoilage"),
                        )
                    else:
                        maturation_info = MaturationInfo(
                            score=getattr(result.maturation_level, "score", 0.0),
                            category=getattr(result.maturation_level, "category", "unknown"),
                            estimated_days_until_spoilage=getattr(
                                result.maturation_level, "estimated_days_until_spoilage", None
                            ),
                        )

                contract_result = ContractDetectionResult(
                    class_name=result.class_name,
                    confidence=result.confidence,
                    bounding_box=result.bounding_box,
                    maturation_level=maturation_info,
                )
                contract_results.append(contract_result)

        if detection_data.summary:
            detection_summary = detection_data.summary
        else:
            detection_summary = ContractDetectionSummary(
                total_objects=len(contract_results),
                objects_with_maturation=sum(1 for r in contract_results if r.maturation_level is not None),
                detection_time_ms=0,
                maturation_time_ms=0,
                average_maturation_score=(
                    sum(r.maturation_level.score for r in contract_results if r.maturation_level)
                    / max(1, sum(1 for r in contract_results if r.maturation_level))
                ),
                model_versions=None,
            )

        contract_detection = ContractDetection(results=contract_results, summary=detection_summary)

        return CombinedContractResponse(
            status=combined_result.status,
            request_id=combined_result.request_id,
            detection=contract_detection,
            image_result_url=combined_result.image_result_url,
            processing_time_ms=combined_result.processing_time_ms,
            processing_metadata=combined_result.processing_metadata,
        )
