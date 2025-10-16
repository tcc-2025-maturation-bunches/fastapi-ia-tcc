import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict

from src.app.config import settings
from src.processor.processing_service import ProcessingService

logger = logging.getLogger()
logger.setLevel(getattr(logging, settings.LOG_LEVEL))


async def process_message_async(processing_service: ProcessingService, message_body: Dict[str, Any], message_id: str):
    try:
        result = await processing_service.process_message(message_body)
        logger.info(f"Mensagem {message_id} processada com sucesso")
        return {"success": True, "message_id": message_id, "result": result}
    except Exception as e:
        logger.exception(f"Erro ao processar mensagem {message_id}: {e}")
        return {
            "success": False,
            "message_id": message_id,
            "error": str(e),
            "request_id": message_body.get("request_id"),
        }


def lambda_handler(event, context):
    logger.info("=== Lambda Processing AI Iniciada ===")
    logger.info(f"Versão: {settings.SERVICE_VERSION} | Ambiente: {settings.ENVIRONMENT}")

    if "Records" not in event or not event["Records"]:
        logger.warning("Nenhuma mensagem SQS encontrada no evento")
        return {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "message": "Nenhuma mensagem para processar",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            ),
        }

    try:
        processing_service = ProcessingService()
    except Exception as e:
        logger.exception(f"Erro ao inicializar ProcessingService: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps(
                {
                    "error": "Erro ao inicializar serviço",
                    "message": str(e),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            ),
        }

    sqs_records = [r for r in event["Records"] if r.get("eventSource") == "aws:sqs"]

    tasks = []
    for record in sqs_records:
        message_id = record.get("messageId", "unknown")
        try:
            message_body = json.loads(record["body"])
            task = process_message_async(processing_service, message_body, message_id)
            tasks.append(task)
        except json.JSONDecodeError as e:
            logger.error(f"Erro ao decodificar JSON da mensagem {message_id}: {e}")

    results = asyncio.run(asyncio.gather(*tasks, return_exceptions=True))

    successful = sum(1 for r in results if isinstance(r, dict) and r.get("success"))
    failed = len(results) - successful

    logger.info(f"Processamento concluído - Sucesso: {successful}, Falhas: {failed}")

    batch_item_failures = []
    for result in results:
        if isinstance(result, dict) and not result.get("success"):
            batch_item_failures.append({"itemIdentifier": result.get("message_id")})

    if batch_item_failures:
        return {"batchItemFailures": batch_item_failures}

    return {
        "statusCode": 200,
        "body": json.dumps(
            {
                "message": "Processamento concluído",
                "processed_count": successful,
                "failed_count": failed,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        ),
    }
