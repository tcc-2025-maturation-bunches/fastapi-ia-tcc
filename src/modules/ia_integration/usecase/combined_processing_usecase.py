import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from src.modules.ia_integration.repo.ia_repository import IARepository
from src.modules.storage.repo.dynamo_repository import DynamoRepository
from src.modules.storage.repo.s3_repository import S3Repository
from src.shared.domain.entities.combined_result import CombinedResult
from src.shared.domain.entities.image import Image
from src.shared.domain.models.http_models import ProcessingStatusResponse
from src.shared.mappers.request_summary_mapper import RequestSummaryMapper

logger = logging.getLogger(__name__)


class CombinedProcessingUseCase:

    def __init__(
        self,
        ia_repository: Optional[IARepository] = None,
        dynamo_repository: Optional[DynamoRepository] = None,
        s3_repository: Optional[S3Repository] = None,
    ):
        self.ia_repository = ia_repository or IARepository()
        self.dynamo_repository = dynamo_repository or DynamoRepository()
        self.s3_repository = s3_repository or S3Repository()

    async def start_processing(
        self,
        image_url: str,
        user_id: str,
        metadata: Optional[Dict[str, Any]] = None,
        maturation_threshold: float = 0.6,
        result_upload_url: Optional[str] = None,
    ) -> str:
        request_id = f"req-combined-{uuid.uuid4().hex[:8]}"

        await self._save_processing_status(
            request_id,
            {
                "status": "queued",
                "image_url": image_url,
                "user_id": user_id,
                "createdAt": datetime.now(timezone.utc).isoformat(),
                "updatedAt": datetime.now(timezone.utc).isoformat(),
                "progress": 0.0,
                "maturation_threshold": maturation_threshold,
                "location": metadata.get("location") if metadata else None,
                "image_id": metadata.get("image_id") if metadata else None,
                "combined_complete": False,
                "combined_id": None,
                "error": None,
                "result_upload_url": result_upload_url,
            },
        )

        logger.info(f"Processamento combinado iniciado: {request_id} para imagem {image_url}")
        return request_id

    async def execute_in_background(
        self,
        request_id: str,
        image_url: str,
        user_id: str,
        metadata: Optional[Dict[str, Any]] = None,
        maturation_threshold: float = 0.6,
        result_upload_url: Optional[str] = None,
    ) -> None:
        try:
            status_data = await self._get_processing_status_data(request_id)
            if not status_data:
                logger.error(f"ID de solicitação não encontrado: {request_id}")
                return

            await self._update_processing_status(request_id, status="processing", progress=0.1)

            image = Image(
                image_url=image_url,
                user_id=user_id,
                metadata=metadata,
                image_id=metadata.get("image_id") if metadata else None,
            )

            await self._update_processing_status(request_id, image_id=image.image_id, progress=0.2)

            if not result_upload_url:
                result_filename = f"{image.image_id}_combined_result.jpg"
                result_presigned_data = await self.s3_repository.generate_result_presigned_url(
                    key=await self.s3_repository.generate_result_key(result_filename, user_id),
                    content_type="image/jpeg",
                )
                result_upload_url = result_presigned_data["upload_url"]

            await self._update_processing_status(request_id, status="processing_combined", progress=0.3)

            combined_result = await self.ia_repository.process_combined(
                image=image,
                result_upload_url=result_upload_url,
                maturation_threshold=maturation_threshold,
            )

            full_metadata = metadata or {}
            full_metadata["image_url"] = image_url
            full_metadata["image_id"] = image.image_id
            if "timestamp" not in full_metadata:
                full_metadata["timestamp"] = datetime.now(timezone.utc).isoformat()

            final_item = RequestSummaryMapper.to_dynamo_item(
                user_id=user_id, request_id=request_id, initial_metadata=full_metadata, combined_result=combined_result
            )

            await self.dynamo_repository.save_request_summary(final_item)

            await self._update_processing_status(request_id, status="completed", progress=1.0)

            logger.info(f"Processamento combinado concluído: {request_id} para imagem {image.image_id}")

        except Exception as e:
            logger.exception(f"Erro no processamento combinado em background: {e}")
            await self._update_processing_status(
                request_id,
                status="error",
                progress=1.0,
                error=str(e),
                error_code="PROCESSING_ERROR",
                error_message="Erro interno no processamento",
            )

    async def execute(
        self,
        image_url: str,
        user_id: str,
        metadata: Optional[Dict[str, Any]] = None,
        maturation_threshold: float = 0.6,
        result_upload_url: Optional[str] = None,
    ) -> CombinedResult:
        try:
            logger.info(f"Iniciando processamento combinado para imagem: {image_url}")

            image = Image(
                image_url=image_url,
                user_id=user_id,
                metadata=metadata,
                image_id=metadata.get("image_id") if metadata else None,
            )
            await self.dynamo_repository.save_image_metadata(image)

            if not result_upload_url:
                result_filename = f"{image.image_id}_combined_result.jpg"
                result_presigned_data = await self.s3_repository.generate_result_presigned_url(
                    key=await self.s3_repository.generate_result_key(result_filename, user_id),
                    content_type="image/jpeg",
                )
                result_upload_url = result_presigned_data["upload_url"]

            combined_result = await self.ia_repository.process_combined(
                image=image,
                result_upload_url=result_upload_url,
                maturation_threshold=maturation_threshold,
            )

            await self.dynamo_repository.save_combined_result(user_id, combined_result)
            return combined_result

        except Exception as e:
            logger.exception(f"Erro no caso de uso de processamento combinado: {e}")
            if "image" in locals():
                return CombinedResult(
                    status="error",
                    error_message="Erro interno no processamento",
                    error_code="PROCESSING_ERROR",
                    error_details={"original_error": str(e)},
                )
            raise

    async def get_combined_result(self, image_id: str) -> Optional[CombinedResult]:
        """Recupera resultado combinado por image_id."""
        try:
            return await self.dynamo_repository.get_combined_result(image_id)
        except Exception as e:
            logger.exception(f"Erro ao recuperar resultado combinado para imagem {image_id}: {e}")
            raise

    async def get_result_by_request_id(self, request_id: str) -> Optional[Dict[str, Any]]:
        try:
            result = await self.dynamo_repository.query_items(
                key_name="request_id", key_value=request_id, index_name="RequestIdIndex"
            )

            items = result.get("items", []) if isinstance(result, dict) else result
            if not items:
                logger.warning(f"Nenhum resultado encontrado para request_id: {request_id}")
                return None
            combined_results = [item for item in items if item.get("entity_type") == "COMBINED_RESULT"]
            if not combined_results:
                logger.warning(f"Nenhum COMBINED_RESULT encontrado para request_id: {request_id}")
                return None
            item = combined_results[0]
            logger.info(f"Resultado combinado encontrado para request_id: {request_id}")

            return {
                "status": item.get("status"),
                "request_id": item.get("request_id"),
                "image_id": item.get("image_id"),
                "image_url": item.get("image_url"),
                "image_result_url": item.get("image_result_url"),
                "user_id": item.get("user_id"),
                "createdAt": item.get("createdAt"),
                "updatedAt": item.get("updatedAt"),
                "processing_time_ms": item.get("processing_time_ms"),
                "detection": item.get("detection_result"),
                "processing_metadata": item.get("processing_metadata"),
                "initial_metadata": item.get("initial_metadata"),
                "additional_metadata": item.get("additional_metadata"),
            }

        except Exception as e:
            logger.exception(f"Erro ao buscar resultado por request_id: {e}")
            raise

    async def get_processing_status(self, request_id: str) -> Optional[ProcessingStatusResponse]:
        """Recupera status do processamento."""
        status_data = await self._get_processing_status_data(request_id)
        if not status_data:
            return None

        return ProcessingStatusResponse(
            request_id=request_id,
            status=status_data.get("status", "unknown"),
            progress=status_data.get("progress", 0.0),
            estimated_completion_time=None,
        )

    async def _save_processing_status(self, request_id: str, status_data: Dict[str, Any]) -> None:
        """Salva o status de processamento no DynamoDB."""
        try:
            status_data["pk"] = f"PROCESSING#{request_id}"
            status_data["sk"] = "STATUS"
            status_data["entity_type"] = "PROCESSING_STATUS"
            status_data["request_id"] = request_id
            status_data["ttl"] = int((datetime.now(timezone.utc).timestamp() + 86400))

            await self.dynamo_repository.save_request_summary(status_data)
        except Exception as e:
            logger.exception(f"Erro ao salvar status de processamento para {request_id}: {e}")
            raise

    async def _get_processing_status_data(self, request_id: str) -> Optional[Dict[str, Any]]:
        """Recupera o status de processamento do DynamoDB."""
        try:
            key = {"pk": f"PROCESSING#{request_id}", "sk": "STATUS"}
            return await self.dynamo_repository.get_item(key)
        except Exception as e:
            logger.exception(f"Erro ao recuperar status de processamento para {request_id}: {e}")
            return None

    async def _update_processing_status(self, request_id: str, **kwargs) -> None:
        """Atualiza o status de processamento no DynamoDB."""
        try:
            status_data = await self._get_processing_status_data(request_id)
            if not status_data:
                logger.warning(f"Tentativa de atualizar status inexistente: {request_id}")
                return

            status_data.update(kwargs)
            status_data["updatedAt"] = datetime.now(timezone.utc).isoformat()

            await self._save_processing_status(request_id, status_data)

        except Exception as e:
            logger.exception(f"Erro ao atualizar status de processamento para {request_id}: {e}")

    async def get_all_combined_results(
        self,
        user_id: Optional[str] = None,
        limit: int = 20,
        last_evaluated_key: Optional[Dict[str, Any]] = None,
        status_filter: Optional[str] = None,
        exclude_errors: bool = False,
    ) -> Dict[str, Any]:
        try:
            query_params = {"limit": limit, "last_evaluated_key": last_evaluated_key}

            if user_id:
                result = await self.dynamo_repository.query_items(
                    key_name="user_id", key_value=user_id, index_name="UserIdIndex", **query_params
                )
                items = result.get("items", []) if isinstance(result, dict) else result
                filtered_items = [item for item in items if item.get("entity_type") == "COMBINED_RESULT"]
            else:
                result = await self.dynamo_repository.query_items(
                    key_name="entity_type", key_value="COMBINED_RESULT", index_name="EntityTypeIndex", **query_params
                )
                filtered_items = result.get("items", []) if isinstance(result, dict) else result

            next_page_key = result.get("last_evaluated_key") if isinstance(result, dict) else None

            combined_results = []
            for item in filtered_items:
                if not item or not isinstance(item, dict):
                    continue

                item_status = item.get("status", "")
                if exclude_errors and item_status == "error":
                    continue
                if status_filter and item_status != status_filter:
                    continue

                try:
                    combined_result = {
                        "status": item.get("status"),
                        "request_id": item.get("request_id"),
                        "image_id": item.get("image_id"),
                        "image_url": item.get("image_url"),
                        "image_result_url": item.get("image_result_url"),
                        "user_id": item.get("user_id"),
                        "createdAt": item.get("createdAt"),
                        "updatedAt": item.get("updatedAt"),
                        "processing_time_ms": item.get("processing_time_ms"),
                        "detection": item.get("detection_result"),
                        "processing_metadata": item.get("processing_metadata"),
                        "initial_metadata": item.get("initial_metadata"),
                        "additional_metadata": item.get("additional_metadata"),
                        **(
                            {
                                "error_message": item.get("error_message"),
                                "error_code": item.get("error_code"),
                                "error_details": item.get("error_details"),
                            }
                            if item_status == "error"
                            else {}
                        ),
                    }
                    combined_results.append(combined_result)
                except Exception as e:
                    logger.warning(f"Erro ao processar item: {e}")
                    continue

            logger.info(f"Recuperados {len(combined_results)} resultados combinados (filtrados)")

            return {
                "items": combined_results,
                "next_page_key": next_page_key,
                "total_count": len(combined_results),
                "has_more": next_page_key is not None,
                "filters_applied": {
                    "status_filter": status_filter,
                    "exclude_errors": exclude_errors,
                    "user_id": user_id,
                },
            }

        except Exception as e:
            logger.exception(f"Erro ao recuperar todos os resultados combinados: {e}")
            raise
