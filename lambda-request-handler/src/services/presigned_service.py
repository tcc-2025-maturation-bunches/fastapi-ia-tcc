import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from botocore.exceptions import ClientError
from fruit_detection_shared.infra.external import S3Client

from src.app.config import settings

logger = logging.getLogger(__name__)


class PresignedURLService:
    def __init__(
        self, images_bucket: Optional[str] = None, results_bucket: Optional[str] = None, region: Optional[str] = None
    ):
        self.images_bucket = images_bucket or settings.S3_IMAGES_BUCKET
        self.results_bucket = results_bucket or settings.S3_RESULTS_BUCKET
        region = region or settings.AWS_REGION

        self.images_client = S3Client(bucket_name=self.images_bucket, region=region)
        self.results_client = S3Client(bucket_name=self.results_bucket, region=region)

    async def generate_upload_url(
        self, filename: str, content_type: str, user_id: str, purpose: str = "image"  # "image" ou "result"
    ) -> Dict[str, Any]:
        try:
            if purpose == "image" and not settings.validate_image_type(content_type):
                raise ValueError(f"Tipo de conteúdo inválido: {content_type}")

            key = self._generate_s3_key(filename, user_id, purpose)
            bucket = self.images_bucket if purpose == "image" else self.results_bucket
            unique_id = key.split("/")[-1].split(".")[0]
            expiry_seconds = settings.PRESIGNED_URL_EXPIRY_MINUTES * 60

            client = self.images_client if purpose == "image" else self.results_client
            presigned_url = client.generate_presigned_url(
                "put_object",
                Params={
                    "Bucket": bucket,
                    "Key": key,
                    "ContentType": content_type,
                    "Metadata": {
                        "user_id": user_id,
                        "original_filename": filename,
                        "upload_timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                },
                ExpiresIn=expiry_seconds,
            )

            public_url = settings.get_s3_url(bucket, key)
            logger.info(f"URL presigned gerada para {purpose}: {unique_id}")

            return {
                "upload_url": presigned_url,
                "public_url": public_url,
                f"{purpose}_id": unique_id,
                "key": key,
                "bucket": bucket,
                "expires_in_seconds": expiry_seconds,
                "expires_at": (datetime.now(timezone.utc) + timedelta(seconds=expiry_seconds)).isoformat(),
            }

        except ClientError as e:
            logger.exception(f"Erro ao gerar URL presigned: {e}")
            raise Exception(f"Falha ao gerar URL de upload: {str(e)}")
        except Exception as e:
            logger.exception(f"Erro inesperado no serviço de URL presigned: {e}")
            raise

    async def generate_download_url(self, key: str, bucket: Optional[str] = None, expiry_minutes: int = 60) -> str:
        try:
            bucket = bucket or self.images_bucket

            presigned_url = self.s3_client.generate_presigned_url(
                "get_object", Params={"Bucket": bucket, "Key": key}, ExpiresIn=expiry_minutes * 60
            )

            logger.info(f"URL de download gerada para chave: {key}")
            return presigned_url

        except ClientError as e:
            logger.exception(f"Erro ao gerar URL de download: {e}")
            raise Exception(f"Falha ao gerar URL de download: {str(e)}")

    async def validate_file_exists(self, key: str, bucket: Optional[str] = None) -> bool:
        try:
            bucket = bucket or self.images_bucket

            self.s3_client.head_object(Bucket=bucket, Key=key)
            return True

        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return False
            logger.exception(f"Erro ao verificar existência do arquivo: {e}")
            raise

    def _generate_s3_key(self, filename: str, user_id: str, purpose: str = "image") -> str:
        ext = filename.split(".")[-1] if "." in filename else "jpg"
        unique_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        year = now.year
        month = now.month
        day = now.day

        if purpose == "image":
            key = f"{user_id}/{year}/{month:02d}/{day:02d}/{unique_id}.{ext}"
        else:
            key = f"{user_id}/{year}/{month:02d}/{day:02d}/{unique_id}_result.{ext}"

        return key

    async def generate_batch_urls(self, requests: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
        results = []

        for request in requests:
            try:
                url_data = await self.generate_upload_url(
                    filename=request["filename"],
                    content_type=request["content_type"],
                    user_id=request["user_id"],
                    purpose=request.get("purpose", "image"),
                )
                results.append({"success": True, **url_data})
            except Exception as e:
                results.append({"success": False, "error": str(e), "filename": request["filename"]})

        return results
