import asyncio
import logging
import time
from typing import Any, Dict, List, Optional

from fruit_detection_shared.domain.entities import CombinedResult, Image
from fruit_detection_shared.domain.models import (
    ContractDetection,
    ContractDetectionResult,
    ContractDetectionSummary,
    ImageDimensions,
    MaturationDistribution,
    MaturationInfo,
    ProcessingMetadata,
)

from src.processor.repository.ia_repository import IARepository
from src.processor.utils.circuit_breaker import CircuitBreaker

logger = logging.getLogger(__name__)


class IAService:
    _instance = None
    _lock = asyncio.Lock()

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(
        self,
        ia_repository: Optional[IARepository] = None,
        circuit_breaker: Optional[CircuitBreaker] = None,
    ):
        if not hasattr(self, "initialized"):
            self.ia_repository = ia_repository or IARepository()
            self.circuit_breaker = circuit_breaker or CircuitBreaker(
                failure_threshold=3,
                timeout_duration=60,
                half_open_attempts=2,
            )
            self._health_cache = {"status": False, "last_check": 0}
            self._health_cache_ttl = 30
            self.initialized = True

    async def _check_health_cached(self) -> bool:
        current_time = time.time()

        if current_time - self._health_cache["last_check"] < self._health_cache_ttl:
            return self._health_cache["status"]

        try:
            is_healthy = await asyncio.wait_for(self.ia_repository.health_check(), timeout=5.0)
            self._health_cache = {"status": is_healthy, "last_check": current_time}
            return is_healthy
        except asyncio.TimeoutError:
            logger.warning("Health check timeout, usando cache")
            return self._health_cache["status"]
        except Exception as e:
            logger.error(f"Health check error: {e}")
            return False

    async def process_image(
        self,
        image: Image,
        result_upload_url: Optional[str],
        maturation_threshold: float = 0.6,
    ) -> CombinedResult:
        try:
            is_healthy = await self._check_health_cached()

            if not is_healthy:
                logger.warning("Serviço de IA reportado como não saudável")
                return CombinedResult(
                    status="error",
                    error_message="Serviço de IA temporariamente indisponível",
                    error_code="IA_SERVICE_UNAVAILABLE",
                    error_details={
                        "circuit_breaker_state": self.circuit_breaker.get_state(),
                        "health_check": False,
                    },
                )

            raw_response = await self.circuit_breaker.call(
                self.ia_repository.request_combined_processing,
                image=image,
                result_upload_url=result_upload_url,
                maturation_threshold=maturation_threshold,
            )

            if raw_response.get("status") == "error":
                return self._create_error_result(raw_response)

            return self._transform_response_to_result(raw_response)

        except Exception as e:
            logger.exception(f"Erro crítico ao processar imagem: {e}")
            return CombinedResult(
                status="error",
                error_message=f"Erro no processamento: {str(e)}",
                error_code="PROCESSING_ERROR",
                error_details={
                    "original_error": str(e),
                    "circuit_breaker_state": self.circuit_breaker.get_state(),
                },
            )

    def get_circuit_breaker_state(self) -> Dict[str, Any]:
        return self.circuit_breaker.get_state()

    def _transform_response_to_result(self, response: Dict[str, Any]) -> CombinedResult:
        detection_results = self._build_detection_results(response.get("detection", {}).get("results", []))

        summary = self._build_summary(response.get("detection", {}).get("summary", {}), len(detection_results))

        detection = ContractDetection(results=detection_results, summary=summary)

        processing_metadata = self._build_processing_metadata(response.get("processing_metadata"))

        return CombinedResult(
            status=response.get("status", "success"),
            request_id=response.get("request_id"),
            detection=detection,
            image_result_url=response.get("image_result_url"),
            processing_time_ms=int(response.get("processing_time_ms", 0)),
            processing_metadata=processing_metadata,
        )

    def _build_detection_results(self, results_data: List[Dict]) -> List[ContractDetectionResult]:
        detection_results = []

        for result in results_data:
            try:
                maturation_level = None
                if result.get("maturation_level"):
                    maturation_level = MaturationInfo(
                        score=float(result["maturation_level"].get("score", 0.0)),
                        category=result["maturation_level"].get("category", "unknown"),
                    )

                detection_results.append(
                    ContractDetectionResult(
                        class_name=result["class_name"],
                        confidence=float(result["confidence"]),
                        bounding_box=[float(x) for x in result["bounding_box"]],
                        maturation_level=maturation_level,
                    )
                )
            except (KeyError, ValueError, TypeError) as e:
                logger.warning(f"Erro ao processar resultado de detecção: {e}")
                continue

        return detection_results

    def _build_summary(self, summary_data: Dict[str, Any], results_count: int) -> ContractDetectionSummary:
        if not summary_data:
            return ContractDetectionSummary(
                total_objects=results_count,
                objects_with_maturation=0,
                detection_time_ms=0,
                maturation_time_ms=0,
                average_maturation_score=0.0,
                model_versions=None,
            )

        model_versions_data = summary_data.get("model_versions", {})
        model_versions = self._normalize_model_versions(model_versions_data)
        average_score = summary_data.get("average_maturation_score")

        return ContractDetectionSummary(
            total_objects=int(summary_data.get("total_objects", results_count)),
            objects_with_maturation=int(summary_data.get("objects_with_maturation", 0)),
            detection_time_ms=int(summary_data.get("detection_time_ms", 0)),
            maturation_time_ms=int(summary_data.get("maturation_time_ms", 0)),
            average_maturation_score=float(average_score) if average_score is not None else 0.0,
            model_versions=model_versions,
        )

    def _normalize_model_versions(self, model_versions_data: Any) -> Dict[str, str]:
        if isinstance(model_versions_data, dict):
            return {
                "detection": str(model_versions_data.get("detection", "unknown")),
                "maturation": str(model_versions_data.get("maturation", "unknown")),
                "segmentation": str(model_versions_data.get("segmentation", "unknown")),
            }

        return {
            "detection": "unknown",
            "maturation": "unknown",
            "segmentation": "unknown",
        }

    def _build_processing_metadata(self, metadata_data: Optional[Dict]) -> Optional[ProcessingMetadata]:
        if not metadata_data:
            return None

        try:
            image_dims = metadata_data.get("image_dimensions", {})
            mat_dist = metadata_data.get("maturation_distribution", {})

            return ProcessingMetadata(
                image_dimensions=ImageDimensions(
                    width=int(image_dims.get("width", 0)),
                    height=int(image_dims.get("height", 0)),
                ),
                maturation_distribution=MaturationDistribution(
                    verde=int(mat_dist.get("verde", 0)),
                    quase_madura=int(mat_dist.get("quase_madura", 0)),
                    madura=int(mat_dist.get("madura", 0)),
                    muito_madura=int(mat_dist.get("muito_madura", 0)),
                    passada=int(mat_dist.get("passada", 0)),
                    nao_analisado=int(mat_dist.get("nao_analisado", 0)),
                ),
            )
        except (KeyError, ValueError, TypeError) as e:
            logger.warning(f"Erro ao construir processing metadata: {e}")
            return None

    def _create_error_result(self, response: Dict[str, Any]) -> CombinedResult:
        return CombinedResult(
            status="error",
            error_message=response.get("error_message", "Erro desconhecido"),
            error_code=response.get("error_code", "PROCESSING_ERROR"),
            error_details=response.get("error_details"),
        )
