import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, BinaryIO, Dict, Optional

from src.app.config import settings
from src.shared.infra.external.s3.s3_client import S3Client

logger = logging.getLogger(__name__)


class S3Repository:

    def __init__(
        self,
        images_bucket: str = "fruit-detection-images",
        results_bucket: str = "fruit-detection-results",
        region: Optional[str] = None,
    ):
        self.images_bucket = settings.S3_IMAGES_BUCKET or images_bucket
        self.results_bucket = settings.S3_RESULTS_BUCKET or results_bucket
        self.region = region or settings.AWS_REGION

        self.images_client = S3Client(bucket_name=images_bucket, region=self.region)
        self.results_client = S3Client(bucket_name=results_bucket, region=self.region)

        logger.info(f"Inicializando repositório S3 com buckets: {images_bucket} e {results_bucket}")

    async def generate_presigned_url(
        self, key: str, content_type: str, expires_in: timedelta = timedelta(minutes=15)
    ) -> Dict[str, Any]:
        logger.info(f"Gerando URL pré-assinada para upload de imagem: {key}")
        return await self.images_client.generate_presigned_url(key, content_type, expires_in)

    async def generate_result_presigned_url(
        self, key: str, content_type: str, expires_in: timedelta = timedelta(minutes=15)
    ) -> Dict[str, Any]:
        logger.info(f"Gerando URL pré-assinada para upload de resultado: {key}")
        return await self.results_client.generate_presigned_url(key, content_type, expires_in)

    async def generate_image_key(self, original_filename: str, user_id: str) -> str:
        if "." in original_filename:
            ext = original_filename.split(".")[-1]
        else:
            ext = "jpg"

        unique_id = str(uuid.uuid4())

        now = datetime.now(timezone.utc)
        return f"{user_id}/{now.year}/{now.month:02d}/{now.day:02d}/{unique_id}.{ext}"

    async def generate_result_key(self, original_filename: str, user_id: str) -> str:
        if "." in original_filename:
            ext = original_filename.split(".")[-1]
        else:
            ext = "jpg"

        unique_id = str(uuid.uuid4())

        now = datetime.now(timezone.utc)
        return f"{user_id}/{now.year}/{now.month:02d}/{now.day:02d}/{unique_id}_result.{ext}"

    async def upload_file(
        self,
        file_obj: BinaryIO,
        key: str,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> str:
        logger.info(f"Fazendo upload de arquivo para o S3: {key}")
        return await self.images_client.upload_file(file_obj, key, content_type, metadata)

    async def upload_result_image(
        self,
        file_obj: BinaryIO,
        original_key: str,
        result_type: str,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> str:
        result_key = original_key.replace(".jpg", f"_{result_type}.jpg")

        logger.info(f"Fazendo upload de imagem de resultado para o S3: {result_key}")
        return await self.results_client.upload_file(file_obj, result_key, content_type, metadata)

    async def get_file_url(self, key: str) -> str:
        return await self.images_client.get_file_url(key)

    async def get_result_url(self, key: str) -> str:
        return await self.results_client.get_file_url(key)

    async def delete_file(self, key: str) -> bool:
        logger.info(f"Excluindo arquivo do S3: {key}")
        return await self.images_client.delete_file(key)

    async def delete_result(self, key: str) -> bool:
        logger.info(f"Excluindo arquivo de resultado do S3: {key}")
        return await self.results_client.delete_file(key)
