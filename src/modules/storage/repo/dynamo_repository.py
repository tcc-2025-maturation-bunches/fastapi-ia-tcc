import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.app.config import settings
from src.shared.domain.entities.combined_result import CombinedResult
from src.shared.domain.entities.image import Image
from src.shared.domain.entities.result import DetectionResult, ProcessingResult
from src.shared.domain.enums.ia_model_type_enum import ModelType
from src.shared.infra.external.dynamo.dynamo_client import DynamoClient
from src.shared.infra.repo.dynamo_repository_interface import DynamoRepositoryInterface

logger = logging.getLogger(__name__)


class DynamoRepository(DynamoRepositoryInterface):
    """Implementação do repositório do DynamoDB."""

    def __init__(self, dynamo_client: Optional[DynamoClient] = None):
        self.results_client = dynamo_client or DynamoClient(table_name=settings.DYNAMODB_TABLE_NAME)

        logger.info(f"Inicializando DynamoRepository para tabela de resultados: {settings.DYNAMODB_TABLE_NAME}")

    async def save_image_metadata(self, image: Image) -> Dict[str, Any]:
        try:
            item = image.to_dict()
            item["pk"] = f"IMG#{image.image_id}"
            item["sk"] = f"META#{image.image_id}"
            item["entity_type"] = "IMAGE"
            item["user_id"] = image.user_id
            item["createdAt"] = image.upload_timestamp.isoformat()
            item["updatedAt"] = image.upload_timestamp.isoformat()

            logger.info(f"Salvando metadados da imagem {image.image_id} na tabela de resultados")
            return await self.results_client.put_item(item)

        except Exception as e:
            logger.exception(f"Erro ao salvar metadados da imagem na tabela de resultados: {e}")
            raise

    async def save_processing_result(self, result: ProcessingResult) -> Dict[str, Any]:
        try:
            item = result.to_dict()
            item["pk"] = f"IMG#{result.image_id}"
            item["sk"] = f"RESULT#{result.request_id}"
            item["entity_type"] = "RESULT"
            item["model_type"] = result.model_type.value
            item["createdAt"] = result.processing_timestamp.isoformat()
            item["updatedAt"] = result.processing_timestamp.isoformat()

            logger.info(f"Salvando resultado de processamento {result.request_id} na tabela de resultados")
            return await self.results_client.put_item(item)

        except Exception as e:
            logger.exception(f"Erro ao salvar resultado de processamento na tabela de resultados: {e}")
            raise

    async def get_image_by_id(self, image_id: str) -> Optional[Image]:
        try:
            key = {"pk": f"IMG#{image_id}", "sk": f"META#{image_id}"}
            item = await self.results_client.get_item(key)

            if not item:
                logger.warning(f"Imagem não encontrada na tabela de resultados: {image_id}")
                return None

            return Image.from_dict(item)

        except Exception as e:
            logger.exception(f"Erro ao recuperar imagem da tabela de resultados: {e}")
            raise

    async def get_result_by_request_id(self, request_id: str) -> Optional[ProcessingResult]:
        try:
            items = await self.results_client.query_items(
                key_name="request_id", key_value=request_id, index_name="RequestIdIndex"
            )

            if items and len(items) > 0:
                return ProcessingResult.from_dict(items[0])

            logger.info(f"Não encontrado resultado simples para {request_id}, buscando em resultados combinados")

            combined_items = await self.results_client.scan(
                filter_expression="entity_type = :entity_type AND request_id = :request_id",
                expression_values={":entity_type": "COMBINED_RESULT", ":request_id": request_id},
            )

            if combined_items and len(combined_items) > 0:
                combined_result = CombinedResult.from_dict(combined_items[0])
                return self._convert_combined_to_processing_result(combined_result, combined_items[0])

            logger.warning(f"Resultado não encontrado para request_id: {request_id}")
            return None

        except Exception as e:
            logger.exception(f"Erro ao recuperar resultado por request_id da tabela de resultados: {e}")
            raise

    async def get_results_by_image_id(self, image_id: str) -> List[ProcessingResult]:
        try:
            result = await self.results_client.query_items(key_name="pk", key_value=f"IMG#{image_id}")
            items = result.get("items", []) if isinstance(result, dict) else result

            results = []
            for item in items:
                if item.get("entity_type") == "RESULT":
                    results.append(ProcessingResult.from_dict(item))

            logger.info(f"Recuperados {len(results)} resultados para imagem {image_id}")
            return results

        except Exception as e:
            logger.exception(f"Erro ao recuperar resultados por image_id da tabela de resultados: {e}")
            raise

    async def get_results_by_user_id(self, user_id: str, limit: int = 10) -> List[ProcessingResult]:
        try:
            result = await self.results_client.query_items(
                key_name="user_id", key_value=user_id, index_name="UserIdIndex", limit=limit
            )
            items = result.get("items", []) if isinstance(result, dict) else result

            results = []
            for item in items:
                if item.get("entity_type") == "RESULT":
                    results.append(ProcessingResult.from_dict(item))

            logger.info(f"Recuperados {len(results)} resultados para usuário {user_id}")
            return results

        except Exception as e:
            logger.exception(f"Erro ao recuperar resultados por user_id da tabela de resultados: {e}")
            raise

    async def save_combined_result(self, user_id: str, combined_result: CombinedResult) -> Dict[str, Any]:
        try:
            item = combined_result.to_contract_dict()

            now = combined_result.processing_metadata.timestamp if combined_result.processing_metadata else None
            if not now:
                from datetime import datetime, timezone

                now = datetime.now(timezone.utc).isoformat()

            item["pk"] = f"USER#{user_id}"
            item["sk"] = f"COMBINED#{now}#{combined_result.request_id}"
            item["entity_type"] = "COMBINED_RESULT"
            item["user_id"] = user_id
            item["request_id"] = combined_result.request_id
            item["createdAt"] = now
            item["updatedAt"] = now

            logger.info(f"Salvando resultado combinado {combined_result.request_id} na tabela de resultados")
            return await self.results_client.put_item(item)

        except Exception as e:
            logger.exception(f"Erro ao salvar resultado combinado na tabela de resultados: {e}")
            raise

    async def get_combined_result(self, image_id: str) -> Optional[CombinedResult]:
        try:
            items = await self.results_client.scan(
                filter_expression="entity_type = :entity_type AND contains(#item, :image_id)",
                expression_values={":entity_type": "COMBINED_RESULT", ":image_id": image_id},
                expression_names={"#item": "image_id"},
            )

            if not items:
                logger.warning(f"Resultado combinado não encontrado para image_id: {image_id}")
                return None

            latest_item = max(items, key=lambda x: x.get("createdAt", ""))
            return CombinedResult.from_dict(latest_item)

        except Exception as e:
            logger.exception(f"Erro ao recuperar resultado combinado da tabela de resultados: {e}")
            raise

    async def save_request_summary(self, item: Dict[str, Any]) -> Dict[str, Any]:
        try:
            logger.info(f"Salvando resumo da requisição {item.get('request_id')} na tabela de resultados")
            return await self.results_client.put_item(item)
        except Exception as e:
            logger.exception(f"Erro ao salvar resumo da requisição na tabela de resultados: {e}")
            raise

    async def get_item(self, key: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            return await self.results_client.get_item(key)
        except Exception as e:
            logger.exception(f"Erro ao recuperar item por chave da tabela de resultados: {e}")
            raise

    async def query_items(
        self,
        key_name: str,
        key_value: Any,
        index_name: Optional[str] = None,
        limit: Optional[int] = None,
        last_evaluated_key: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        try:
            query_kwargs = {
                "KeyConditionExpression": f"{key_name} = :value",
                "ExpressionAttributeValues": {":value": key_value},
            }

            if index_name:
                query_kwargs["IndexName"] = index_name

            if limit:
                query_kwargs["Limit"] = limit

            if last_evaluated_key:
                query_kwargs["ExclusiveStartKey"] = last_evaluated_key

            response = self.results_client.table.query(**query_kwargs)
            items = response.get("Items", [])

            converted_items = [self.results_client.convert_from_dynamo_item(item) for item in items]

            if "LastEvaluatedKey" in response:
                return {"items": converted_items, "last_evaluated_key": response["LastEvaluatedKey"]}

            return {"items": converted_items, "last_evaluated_key": None}

        except Exception as e:
            logger.error(f"Erro ao consultar itens na tabela de resultados: {e}")
            raise

    async def get_all_results(self, limit: int = 50, last_evaluated_key: Optional[Dict[str, Any]] = None):
        try:
            logger.info(f"Buscando todos os resultados de inferência (limit: {limit})")

            result_response = await self._query_by_entity_type("RESULT", limit // 2, last_evaluated_key)
            combined_response = await self._query_by_entity_type("COMBINED_RESULT", limit // 2, None)
            all_items = result_response["items"] + combined_response["items"]
            all_items.sort(key=lambda x: x.get("createdAt", ""), reverse=True)
            limited_items = all_items[:limit]
            next_key = None
            if len(all_items) > limit:
                next_key = {
                    "entity_type": limited_items[-1].get("entity_type"),
                    "createdAt": limited_items[-1].get("createdAt"),
                }
            elif result_response.get("last_evaluated_key") or combined_response.get("last_evaluated_key"):
                next_key = {
                    "RESULT_last_evaluated_key": result_response.get("last_evaluated_key"),
                    "COMBINED_RESULT_last_evaluated_key": combined_response.get("last_evaluated_key"),
                }

            logger.info(f"Retornando {len(limited_items)} resultados de inferência")

            return {"items": limited_items, "last_evaluated_key": next_key}

        except Exception as e:
            logger.exception(f"Erro ao buscar todos os resultados de inferência: {e}")
            raise

    async def _query_by_entity_type(
        self, entity_type: str, limit: int, last_evaluated_key: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        try:
            query_kwargs = {
                "IndexName": "EntityTypeIndex",
                "KeyConditionExpression": "entity_type = :entity_type",
                "ExpressionAttributeValues": {":entity_type": entity_type},
                "ScanIndexForward": False,
                "Limit": limit,
            }

            if entity_type in ["RESULT", "COMBINED_RESULT"]:
                query_kwargs["FilterExpression"] = "#status <> :error_status AND #status <> :processing_status"
                query_kwargs["ExpressionAttributeNames"] = {"#status": "status"}
                query_kwargs["ExpressionAttributeValues"].update(
                    {":error_status": "error", ":processing_status": "processing"}
                )

            if last_evaluated_key:
                query_kwargs["ExclusiveStartKey"] = last_evaluated_key

            response = self.results_client.table.query(**query_kwargs)
            items = response.get("Items", [])

            converted_items = [self.results_client.convert_from_dynamo_item(item) for item in items]

            return {"items": converted_items, "last_evaluated_key": response.get("LastEvaluatedKey")}

        except Exception as e:
            logger.exception(f"Erro ao buscar por entity_type {entity_type}: {e}")
            raise

    async def scan(
        self,
        filter_expression: Optional[str] = None,
        expression_values: Optional[Dict[str, Any]] = None,
        expression_names: Optional[Dict[str, str]] = None,
        limit: Optional[int] = None,
        last_evaluated_key: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        try:
            scan_kwargs = {}

            if filter_expression:
                scan_kwargs["FilterExpression"] = filter_expression
            if expression_values:
                scan_kwargs["ExpressionAttributeValues"] = expression_values
            if expression_names:
                scan_kwargs["ExpressionAttributeNames"] = expression_names
            if limit:
                scan_kwargs["Limit"] = limit
            if last_evaluated_key:
                scan_kwargs["ExclusiveStartKey"] = last_evaluated_key

            response = self.results_client.table.scan(**scan_kwargs)
            items = response.get("Items", [])

            return [self.results_client.convert_from_dynamo_item(item) for item in items]

        except Exception as e:
            logger.error(f"Erro ao realizar scan na tabela de resultados: {e}")
            raise

    def _convert_combined_to_processing_result(
        self, combined_result: CombinedResult, raw_item: Dict[str, Any]
    ) -> ProcessingResult:
        detection_results = []
        if combined_result.detection and combined_result.detection.results:
            for res in combined_result.detection.results:
                detection_results.append(
                    DetectionResult(
                        class_name=res.class_name,
                        confidence=res.confidence,
                        bounding_box=res.bounding_box,
                        maturation_level=res.maturation_level.model_dump() if res.maturation_level else None,
                    )
                )

        return ProcessingResult(
            image_id=raw_item.get("image_id", ""),
            model_type=ModelType.COMBINED,
            results=detection_results,
            status=combined_result.status,
            request_id=combined_result.request_id,
            processing_timestamp=datetime.fromisoformat(
                raw_item.get("createdAt", datetime.now(timezone.utc).isoformat())
            ),
            summary=combined_result.detection.summary.model_dump() if combined_result.detection else {},
            image_result_url=combined_result.image_result_url,
            error_message=combined_result.error_message,
        )
