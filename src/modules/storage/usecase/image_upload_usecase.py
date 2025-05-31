import logging
from datetime import timedelta
from typing import Any, BinaryIO, Dict, Optional

from src.modules.storage.repo.dynamo_repository import DynamoRepository
from src.modules.storage.repo.s3_repository import S3Repository
from src.shared.domain.entities.image import Image

logger = logging.getLogger(__name__)


class ImageUploadUseCase:
    """Caso de uso para upload de imagens."""

    def __init__(
        self,
        s3_repository: Optional[S3Repository] = None,
        dynamo_repository: Optional[DynamoRepository] = None,
    ):
        self.s3_repository = s3_repository or S3Repository()
        self.dynamo_repository = dynamo_repository or DynamoRepository()

    async def generate_presigned_url(self, filename: str, content_type: str, user_id: str) -> Dict[str, Any]:
        try:
            key = await self.s3_repository.generate_image_key(filename, user_id)
            presigned_url_data = await self.s3_repository.generate_presigned_url(
                key=key, content_type=content_type, expires_in=timedelta(minutes=15)
            )

            image_id = key.split("/")[-1].split(".")[0]
            response = {
                "upload_url": presigned_url_data["upload_url"],
                "image_id": image_id,
                "expires_in_seconds": presigned_url_data["expires_in_seconds"],
                "key": key,
            }

            logger.info(f"URL pré-assinada gerada para upload de imagem: {image_id}")
            return response

        except Exception as e:
            logger.exception(f"Erro ao gerar URL pré-assinada: {e}")
            raise
        
    async def generate_result_presigned_url(self, filename: str, content_type: str, user_id: str) -> Dict[str, Any]:
        try:
            key = await self.s3_repository.generate_result_key(filename, user_id)
            presigned_url_data = await self.s3_repository.generate_result_presigned_url(
                key=key, content_type=content_type, expires_in=timedelta(minutes=15)
            )

            response = {
                "upload_url": presigned_url_data["upload_url"],
                "result_id": key.split("/")[-1].split(".")[0],
                "expires_in_seconds": presigned_url_data["expires_in_seconds"],
                "key": key,
            }

            logger.info(f"URL pré-assinada gerada para upload de resultado: {response['result_id']}")
            return response

        except Exception as e:
            logger.exception(f"Erro ao gerar URL pré-assinada para resultado: {e}")
            raise

    async def upload_image(
        self,
        file_obj: BinaryIO,
        filename: str,
        user_id: str,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> Image:
        try:
            key = await self.s3_repository.generate_image_key(filename, user_id)
            image_url = await self.s3_repository.upload_file(
                file_obj=file_obj,
                key=key,
                content_type=content_type,
                metadata={
                    "user_id": user_id,
                    "original_filename": filename,
                    **(metadata or {}),
                },
            )

            image = Image(
                image_url=image_url,
                user_id=user_id,
                metadata={
                    "original_filename": filename,
                    "content_type": content_type,
                    **(metadata or {}),
                },
            )

            await self.dynamo_repository.save_image_metadata(image)

            logger.info(f"Imagem {image.image_id} enviada com sucesso")
            return image

        except Exception as e:
            logger.exception(f"Erro ao fazer upload de imagem: {e}")
            raise
