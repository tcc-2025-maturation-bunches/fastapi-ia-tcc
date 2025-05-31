import logging
from typing import Any, Dict, Optional

from src.modules.ia_integration.repo.ia_repository import IARepository
from src.modules.storage.repo.dynamo_repository import DynamoRepository
from src.modules.storage.repo.s3_repository import S3Repository
from src.shared.domain.entities.image import Image
from src.shared.domain.entities.result import ProcessingResult
from src.shared.domain.enums.ia_model_type_enum import ModelType

logger = logging.getLogger(__name__)


class DetectUseCase:
    def __init__(
        self,
        ia_repository: Optional[IARepository] = None,
        dynamo_repository: Optional[DynamoRepository] = None,
        s3_repository: Optional[S3Repository] = None,
    ):
        self.ia_repository = ia_repository or IARepository()
        self.dynamo_repository = dynamo_repository or DynamoRepository()
        self.s3_repository = s3_repository or S3Repository()

    async def execute(
        self, image_url: str, user_id: str, metadata: Optional[Dict[str, Any]] = None
    ) -> ProcessingResult:
        try:
            logger.info(f"Iniciando detecção de objetos para imagem: {image_url}")
            image = Image(image_url=image_url, user_id=user_id, metadata=metadata)
            await self.dynamo_repository.save_image_metadata(image)

            result_filename = f"{image.image_id}_detection_result.jpg"
            result_presigned_data = await self.s3_repository.generate_result_presigned_url(
                key=await self.s3_repository.generate_result_key(result_filename, user_id), content_type="image/jpeg"
            )

            result = await self.ia_repository.detect_objects(
                image=image, result_upload_url=result_presigned_data["upload_url"]
            )

            await self.dynamo_repository.save_processing_result(result)

            return result

        except Exception as e:
            logger.exception(f"Erro no caso de uso de detecção: {e}")

            return ProcessingResult(
                image_id=image.image_id if "image" in locals() else "unknown",
                model_type=ModelType.DETECTION,
                results=[],
                status="error",
                error_message=f"Erro interno: {str(e)}",
            )
