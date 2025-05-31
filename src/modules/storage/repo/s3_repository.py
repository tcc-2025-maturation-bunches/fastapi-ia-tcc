import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, BinaryIO, Dict, Optional

from src.app.config import settings
from src.shared.infra.external.s3.s3_client import S3Client
from src.shared.infra.repo.s3_repository_interface import S3RepositoryInterface

logger = logging.getLogger(__name__)


class S3Repository(S3RepositoryInterface):
    """Implementação do repositório do S3."""

    def __init__(
        self,
        images_bucket: str = "fruit-detection-images",
        results_bucket: str = "fruit-detection-results",
        region: Optional[str] = None,
    ):
        """
        Inicializa o repositório do S3.

        Args:
            images_bucket: Nome do bucket para armazenar imagens originais
            results_bucket: Nome do bucket para armazenar resultados do processamento
            region: Região da AWS. Se não fornecida, usa a configuração padrão.
        """
        self.images_bucket = settings.S3_IMAGES_BUCKET or images_bucket
        self.results_bucket = settings.S3_RESULTS_BUCKET or results_bucket
        self.region = region or settings.AWS_REGION

        self.images_client = S3Client(bucket_name=images_bucket, region=self.region)
        self.results_client = S3Client(bucket_name=results_bucket, region=self.region)

        logger.info(f"Inicializando repositório S3 com buckets: {images_bucket} e {results_bucket}")

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
            Dict: Dados da URL pré-assinada
        """
        logger.info(f"Gerando URL pré-assinada para upload de imagem: {key}")
        return await self.images_client.generate_presigned_url(key, content_type, expires_in)
    
    async def generate_result_presigned_url(
        self, key: str, content_type: str, expires_in: timedelta = timedelta(minutes=15)
    ) -> Dict[str, Any]:
        """
        Gera uma URL pré-assinada para upload direto para o bucket de resultados.

        Args:
            key: Caminho do objeto no bucket
            content_type: Tipo de conteúdo do arquivo
            expires_in: Tempo de expiração da URL

        Returns:
            Dict: Dados da URL pré-assinada
        """
        logger.info(f"Gerando URL pré-assinada para upload de resultado: {key}")
        return await self.results_client.generate_presigned_url(key, content_type, expires_in)

    async def generate_image_key(self, original_filename: str, user_id: str) -> str:
        """
        Gera uma chave única para a imagem no S3.

        Args:
            original_filename: Nome original do arquivo
            user_id: ID do usuário

        Returns:
            str: Chave gerada
        """
        if "." in original_filename:
            ext = original_filename.split(".")[-1]
        else:
            ext = "jpg"

        unique_id = str(uuid.uuid4())

        now = datetime.now(timezone.utc)
        return f"{user_id}/{now.year}/{now.month:02d}/{now.day:02d}/{unique_id}.{ext}"
    
    async def generate_result_key(self, original_filename: str, user_id: str) -> str:
        """
        Gera uma chave única para o resultado no S3.

        Args:
            original_filename: Nome original do arquivo
            user_id: ID do usuário

        Returns:
            str: Chave gerada
        """
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
        """
        Faz upload de uma imagem de resultado para o S3.

        Args:
            file_obj: Objeto do arquivo
            original_key: Chave da imagem original
            result_type: Tipo do resultado (detection, maturation)
            content_type: Tipo de conteúdo do arquivo
            metadata: Metadados do arquivo

        Returns:
            str: URL do arquivo no S3
        """
        result_key = original_key.replace(".jpg", f"_{result_type}.jpg")

        logger.info(f"Fazendo upload de imagem de resultado para o S3: {result_key}")
        return await self.results_client.upload_file(file_obj, result_key, content_type, metadata)

    async def get_file_url(self, key: str) -> str:
        """
        Obtém a URL de um arquivo no S3.

        Args:
            key: Caminho do objeto no bucket

        Returns:
            str: URL do arquivo no S3
        """
        return await self.images_client.get_file_url(key)

    async def get_result_url(self, key: str) -> str:
        """
        Obtém a URL de um arquivo de resultado no S3.

        Args:
            key: Caminho do objeto no bucket

        Returns:
            str: URL do arquivo no S3
        """
        return await self.results_client.get_file_url(key)

    async def delete_file(self, key: str) -> bool:
        """
        Exclui um arquivo do S3.

        Args:
            key: Caminho do objeto no bucket

        Returns:
            bool: True se a exclusão foi bem-sucedida
        """
        logger.info(f"Excluindo arquivo do S3: {key}")
        return await self.images_client.delete_file(key)

    async def delete_result(self, key: str) -> bool:
        """
        Exclui um arquivo de resultado do S3.

        Args:
            key: Caminho do objeto no bucket

        Returns:
            bool: True se a exclusão foi bem-sucedida
        """
        logger.info(f"Excluindo arquivo de resultado do S3: {key}")
        return await self.results_client.delete_file(key)
