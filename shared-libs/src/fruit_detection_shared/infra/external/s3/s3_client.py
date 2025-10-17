import logging
import mimetypes
from datetime import timedelta
from typing import Any, BinaryIO, Dict, List, Optional

import aioboto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class S3Client:
    _session: Optional[aioboto3.Session] = None

    def __init__(self, bucket_name: str, region: str = "us-east-1"):
        if not bucket_name:
            raise ValueError("bucket_name é obrigatório")

        self.bucket_name = bucket_name
        self.region = region

        if S3Client._session is None:
            S3Client._session = aioboto3.Session()

        self.session = S3Client._session
        logger.info(f"Inicializando cliente S3 assíncrono para bucket {self.bucket_name}")

    async def generate_presigned_url(self, operation: str, params: Dict[str, Any], expires_in: int = 900) -> str:
        async with self.session.client("s3", region_name=self.region) as client:
            try:
                response = await client.generate_presigned_url(
                    operation,
                    Params=params,
                    ExpiresIn=expires_in,
                )
                return response
            except ClientError as e:
                logger.error(f"Erro ao gerar URL pré-assinada: {e}")
                raise

    async def generate_presigned_url_async(
        self, key: str, content_type: str, expires_in: timedelta = timedelta(minutes=15)
    ) -> Dict[str, Any]:
        expires_seconds = int(expires_in.total_seconds())

        async with self.session.client("s3", region_name=self.region) as client:
            try:
                response = await client.generate_presigned_url(
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

    async def upload_fileobj(
        self,
        file_obj: BinaryIO,
        key: str,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> str:
        if not content_type:
            content_type, _ = mimetypes.guess_type(key)
            if not content_type:
                content_type = "application/octet-stream"

        extra_args = {"ContentType": content_type}
        if metadata:
            extra_args["Metadata"] = metadata

        async with self.session.client("s3", region_name=self.region) as client:
            try:
                await client.upload_fileobj(file_obj, self.bucket_name, key, ExtraArgs=extra_args)
                return await self.get_file_url(key)
            except ClientError as e:
                logger.error(f"Erro ao fazer upload de arquivo: {e}")
                raise

    async def upload_file(
        self,
        file_obj: BinaryIO,
        key: str,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> str:
        return await self.upload_fileobj(file_obj, key, content_type, metadata)

    async def get_file_url(self, key: str) -> str:
        return f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{key}"

    async def delete_file(self, key: str) -> bool:
        async with self.session.client("s3", region_name=self.region) as client:
            try:
                await client.delete_object(Bucket=self.bucket_name, Key=key)
                logger.debug(f"Arquivo deletado: {key}")
                return True
            except ClientError as e:
                logger.error(f"Erro ao excluir arquivo: {e}")
                return False

    async def head_object(self, key: str) -> Optional[Dict[str, Any]]:
        async with self.session.client("s3", region_name=self.region) as client:
            try:
                response = await client.head_object(Bucket=self.bucket_name, Key=key)
                return {
                    "content_type": response.get("ContentType"),
                    "content_length": response.get("ContentLength"),
                    "last_modified": response.get("LastModified"),
                    "metadata": response.get("Metadata", {}),
                }
            except ClientError as e:
                if e.response["Error"]["Code"] == "404":
                    return None
                logger.error(f"Erro ao obter metadados do objeto: {e}")
                raise

    async def list_objects(self, prefix: str = "", max_keys: int = 1000) -> List[Dict[str, Any]]:
        async with self.session.client("s3", region_name=self.region) as client:
            try:
                response = await client.list_objects_v2(
                    Bucket=self.bucket_name,
                    Prefix=prefix,
                    MaxKeys=max_keys,
                )

                objects = []
                for obj in response.get("Contents", []):
                    objects.append(
                        {
                            "key": obj["Key"],
                            "size": obj["Size"],
                            "last_modified": obj["LastModified"],
                            "etag": obj["ETag"],
                        }
                    )

                return objects
            except ClientError as e:
                logger.error(f"Erro ao listar objetos: {e}")
                raise

    async def copy_object(self, source_key: str, dest_key: str, dest_bucket: Optional[str] = None) -> bool:
        dest_bucket = dest_bucket or self.bucket_name

        async with self.session.client("s3", region_name=self.region) as client:
            try:
                await client.copy_object(
                    CopySource={"Bucket": self.bucket_name, "Key": source_key},
                    Bucket=dest_bucket,
                    Key=dest_key,
                )
                logger.debug(f"Objeto copiado: {source_key} -> {dest_key}")
                return True
            except ClientError as e:
                logger.error(f"Erro ao copiar objeto: {e}")
                return False

    async def get_object(self, key: str) -> Optional[bytes]:
        async with self.session.client("s3", region_name=self.region) as client:
            try:
                response = await client.get_object(Bucket=self.bucket_name, Key=key)
                async with response["Body"] as stream:
                    return await stream.read()
            except ClientError as e:
                if e.response["Error"]["Code"] == "NoSuchKey":
                    return None
                logger.error(f"Erro ao obter objeto: {e}")
                raise

    async def put_object(
        self,
        key: str,
        body: bytes,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> str:
        if not content_type:
            content_type, _ = mimetypes.guess_type(key)
            if not content_type:
                content_type = "application/octet-stream"

        put_kwargs = {
            "Bucket": self.bucket_name,
            "Key": key,
            "Body": body,
            "ContentType": content_type,
        }

        if metadata:
            put_kwargs["Metadata"] = metadata

        async with self.session.client("s3", region_name=self.region) as client:
            try:
                await client.put_object(**put_kwargs)
                return await self.get_file_url(key)
            except ClientError as e:
                logger.error(f"Erro ao fazer put de objeto: {e}")
                raise
