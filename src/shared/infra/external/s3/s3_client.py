import logging
import mimetypes
from datetime import timedelta
from typing import Any, BinaryIO, Dict, Optional

import boto3
from botocore.exceptions import ClientError

from src.app.config import settings

logger = logging.getLogger(__name__)


class S3Client:
    """Cliente para interação com o Amazon S3."""

    def __init__(self, bucket_name: str, region: Optional[str] = None):
        self.bucket_name = bucket_name
        self.region = region or settings.AWS_REGION
        self.client = boto3.client("s3", region_name=self.region)
        logger.info(f"Inicializando cliente S3 para bucket {self.bucket_name}")

    async def generate_presigned_url(
        self, key: str, content_type: str, expires_in: timedelta = timedelta(minutes=15)
    ) -> Dict[str, Any]:
        """
        Gera uma URL pré-assinada para upload direto para o S3.

        Args:
            key: Caminho do objeto no bucket
            content_type: Tipo de conteúdo do arquivo
            expires_in: Tempo de expiração da URL

        Returns:
            Dict: Dados da URL pré-assinada incluindo a URL e o tempo de expiração
        """
        try:
            expires_seconds = int(expires_in.total_seconds())

            response = self.client.generate_presigned_url(
                "put_object",
                Params={
                    "Bucket": self.bucket_name,
                    "Key": key,
                    "ContentType": content_type,
                },
                ExpiresIn=expires_seconds,
            )

            return {
                "upload_url": response,
                "key": key,
                "expires_in_seconds": expires_seconds,
            }
        except ClientError as e:
            logger.error(f"Erro ao gerar URL pré-assinada: {e}")
            raise

    async def upload_file(
        self,
        file_obj: BinaryIO,
        key: str,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> str:
        """
        Faz upload de um arquivo para o S3.

        Args:
            file_obj: Objeto do arquivo
            key: Caminho do objeto no bucket
            content_type: Tipo de conteúdo do arquivo
            metadata: Metadados do arquivo

        Returns:
            str: URL do arquivo no S3
        """
        try:
            if not content_type:
                content_type, _ = mimetypes.guess_type(key)
                if not content_type:
                    content_type = "application/octet-stream"

            extra_args = {"ContentType": content_type}

            if metadata:
                extra_args["Metadata"] = metadata

            self.client.upload_fileobj(file_obj, self.bucket_name, key, ExtraArgs=extra_args)

            return await self.get_file_url(key)
        except ClientError as e:
            logger.error(f"Erro ao fazer upload de arquivo para S3: {e}")
            raise

    async def get_file_url(self, key: str) -> str:
        """
        Obtém a URL de um arquivo no S3.

        Args:
            key: Caminho do objeto no bucket

        Returns:
            str: URL do arquivo no S3
        """
        return f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{key}"

    async def delete_file(self, key: str) -> bool:
        """
        Exclui um arquivo do S3.

        Args:
            key: Caminho do objeto no bucket

        Returns:
            bool: True se a exclusão foi bem-sucedida
        """
        try:
            self.client.delete_object(Bucket=self.bucket_name, Key=key)
            return True
        except ClientError as e:
            logger.error(f"Erro ao excluir arquivo do S3: {e}")
            return False
