import logging
from typing import Optional

from shared.domain.entities.combined_result import CombinedResult
from shared.domain.models.base_models import ContractDetectionSummary, ProcessingMetadata
from shared.domain.models.combined_models import ContractDetection, ContractDetectionResult
from src.shared.domain.entities.image import Image
from src.shared.domain.entities.result import DetectionResult, ProcessingResult
from src.shared.domain.enums.ia_model_type_enum import ModelType
from src.shared.infra.external.ec2.ec2_client import EC2Client
from src.shared.infra.repo.ia_repository_interface import IARepositoryInterface

logger = logging.getLogger(__name__)


class IARepository(IARepositoryInterface):
    """Implementação do repositório de IA."""

    def __init__(self, ec2_client: Optional[EC2Client] = None):
        self.ec2_client = ec2_client or EC2Client()

    async def detect_objects(self, image: Image, result_upload_url: str) -> ProcessingResult:
        """
        Detecta objetos em uma imagem.

        Args:
            image: Entidade de imagem com URL e metadados
            result_upload_url: URL pré-assinada para upload do resultado

        Returns:
            ProcessingResult: Resultado do processamento com detecções
        """
        try:
            metadata = {
                **(image.metadata or {}),
                "user_id": image.user_id,
                "image_id": image.image_id,
                "timestamp": image.upload_timestamp.isoformat(),
            }

            response = await self.ec2_client.detect_objects(
                image_url=image.image_url, result_upload_url=result_upload_url, metadata=metadata
            )

            if response.get("status") == "error":
                logger.error(f"Erro na detecção de objetos: {response.get('error_message')}")
                return ProcessingResult(
                    image_id=image.image_id,
                    model_type=ModelType.DETECTION,
                    results=[],
                    status="error",
                    error_message=response.get("error_message", "Erro desconhecido no processamento"),
                    request_id=response.get("request_id"),
                    summary=response.get("summary", {}),
                )

            detection_results = []
            for result in response.get("results", []):
                detection_results.append(
                    DetectionResult(
                        class_name=result["class_name"],
                        confidence=result["confidence"],
                        bounding_box=result["bounding_box"],
                        maturation_level=result.get("maturation_level"),
                    )
                )

            return ProcessingResult(
                image_id=image.image_id,
                model_type=ModelType.DETECTION,
                results=detection_results,
                status=response.get("status", "success"),
                request_id=response.get("request_id"),
                summary=response.get("summary", {}),
                image_result_url=response.get("image_result_url"),
            )

        except Exception as e:
            logger.exception(f"Erro ao processar detecção de objetos: {e}")
            return ProcessingResult(
                image_id=image.image_id,
                model_type=ModelType.DETECTION,
                results=[],
                status="error",
                error_message=f"Erro interno: {str(e)}",
            )

    async def process_combined(
        self, image: Image, result_upload_url: str, maturation_threshold: float = 0.6
    ) -> CombinedResult:
        """
        Processa uma imagem com detecção e análise de maturação combinadas.

        Args:
            image: Entidade de imagem com URL e metadados
            result_upload_url: URL pré-assinada para upload do resultado
            maturation_threshold: Limiar de confiança para análise de maturação

        Returns:
            CombinedResult: Resultado do processamento combinado
        """
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
                summary = ContractDetectionSummary(**summary_data)

            processing_metadata = None
            if response.get("processing_metadata"):
                processing_metadata = ProcessingMetadata(**response["processing_metadata"])

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
