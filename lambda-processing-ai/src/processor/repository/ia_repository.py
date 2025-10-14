import logging
from typing import List, Optional

from fruit_detection_shared.domain.entities import CombinedResult, Image
from fruit_detection_shared.domain.models import (
    ContractDetection,
    ContractDetectionResult,
    ContractDetectionSummary,
    ProcessingMetadata,
)
from fruit_detection_shared.infra.external import EC2Client

from src.app.config import settings

logger = logging.getLogger(__name__)


class ModelInfo:
    def __init__(self, name: str, version: str, description: str):
        self.name = name
        self.version = version
        self.description = description


class HealthCheckResponse:
    def __init__(self, status: str, models: List[ModelInfo]):
        self.status = status
        self.models = models

    @property
    def is_healthy(self) -> bool:
        return self.status == "healthy"


class IARepository:
    def __init__(self, ec2_client: Optional[EC2Client] = None):
        self.ec2_client = ec2_client or EC2Client(base_url=settings.EC2_IA_ENDPOINT, timeout=settings.REQUEST_TIMEOUT)

    async def health_check(self) -> bool:
        try:
            health_response = await self._check_health()

            if health_response and health_response.is_healthy:
                model_names = [model.name for model in health_response.models]
                logger.info(f"Serviço de IA saudável. Modelos: {', '.join(model_names)}")
                return True
            else:
                logger.warning("Serviço de IA não está saudável")
                return False

        except Exception as e:
            logger.error(f"Erro ao verificar health do serviço de IA: {e}")
            return False

    async def _check_health(self) -> Optional[HealthCheckResponse]:
        try:
            import aiohttp

            health_url = f"{self.ec2_client.base_url}/health"

            async with aiohttp.ClientSession() as session:
                async with session.get(health_url, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()

                        models = []
                        for model_data in data.get("models", []):
                            models.append(
                                ModelInfo(
                                    name=model_data.get("name", "unknown"),
                                    version=model_data.get("version", "unknown"),
                                    description=model_data.get("description", ""),
                                )
                            )

                        return HealthCheckResponse(status=data.get("status", "unknown"), models=models)
                    else:
                        logger.error(f"Health check retornou status {response.status}")
                        return None

        except Exception as e:
            logger.error(f"Falha ao conectar ao endpoint de health: {e}")
            return None

    async def process_combined(
        self, image: Image, result_upload_url: Optional[str], maturation_threshold: float = 0.6
    ) -> CombinedResult:
        try:
            metadata = {
                **(image.metadata or {}),
                "user_id": image.user_id,
                "image_id": image.image_id,
                "timestamp": image.upload_timestamp.isoformat(),
            }

            response = await self.ec2_client.process_combined(
                image_url=image.image_url,
                result_upload_url=result_upload_url,
                maturation_threshold=maturation_threshold,
                metadata=metadata,
            )

            detection_results = []
            for result in response.get("detection", {}).get("results", []):
                detection_results.append(
                    ContractDetectionResult(
                        class_name=result["class_name"],
                        confidence=result["confidence"],
                        bounding_box=result["bounding_box"],
                        maturation_level=result.get("maturation_level"),
                    )
                )

            summary_data = response.get("detection", {}).get("summary", {})
            summary = None
            if summary_data:
                model_versions_data = summary_data.get("model_versions", {})

                if isinstance(model_versions_data, dict):
                    model_versions_normalized = {
                        "detection": model_versions_data.get("detection", "unknown"),
                        "maturation": model_versions_data.get("maturation", "unknown"),
                        "segmentation": model_versions_data.get("segmentation", "unknown"),
                    }
                else:
                    model_versions_normalized = {
                        "detection": "unknown",
                        "maturation": "unknown",
                        "segmentation": "unknown",
                    }

                summary = ContractDetectionSummary(
                    total_objects=summary_data.get("total_objects", 0),
                    objects_with_maturation=summary_data.get("objects_with_maturation", 0),
                    detection_time_ms=summary_data.get("detection_time_ms", 0),
                    maturation_time_ms=summary_data.get("maturation_time_ms", 0),
                    average_maturation_score=summary_data.get("average_maturation_score", 0.0),
                    model_versions=model_versions_normalized,
                )

            processing_metadata = None
            if response.get("processing_metadata"):
                metadata_data = response["processing_metadata"]

                image_dims = metadata_data.get("image_dimensions", {})
                mat_dist = metadata_data.get("maturation_distribution", {})

                mat_dist_normalized = {
                    "verde": mat_dist.get("verde", 0),
                    "quase_madura": mat_dist.get("quase_madura", 0),
                    "madura": mat_dist.get("madura", 0),
                    "muito_madura": mat_dist.get("muito_madura", 0),
                    "passada": mat_dist.get("passada", 0),
                    "nao_analisado": mat_dist.get("nao_analisado", 0),
                }

                processing_metadata = ProcessingMetadata(
                    image_dimensions=image_dims,
                    maturation_distribution=mat_dist_normalized,
                )

            status = response.get("status", "success")
            error_code = response.get("error_code")
            error_message = response.get("error_message")
            error_details = response.get("error_details")

            return CombinedResult(
                status=status,
                request_id=response.get("request_id"),
                detection=ContractDetection(
                    results=detection_results,
                    summary=(
                        summary
                        if summary
                        else ContractDetectionSummary(
                            total_objects=0,
                            objects_with_maturation=0,
                            detection_time_ms=0,
                            maturation_time_ms=0,
                            average_maturation_score=0.0,
                            model_versions=None,
                        )
                    ),
                ),
                image_result_url=response.get("image_result_url"),
                processing_time_ms=response.get("processing_time_ms", 0),
                processing_metadata=processing_metadata,
                error_code=error_code,
                error_message=error_message,
                error_details=error_details,
            )

        except Exception as e:
            logger.exception(f"Erro ao processar análise combinada: {e}")
            return CombinedResult(
                status="error",
                error_message=f"Erro interno: {str(e)}",
                error_code="PROCESSING_ERROR",
                error_details={"original_error": str(e)},
            )
