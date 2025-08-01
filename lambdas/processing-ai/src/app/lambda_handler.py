import json
import logging
from datetime import datetime, timezone

from src.app.config import settings
from src.processor.processing_service import ProcessingService

logger = logging.getLogger()
logger.setLevel(getattr(logging, settings.LOG_LEVEL))


def lambda_handler(event, context):
    logger.info(f"Lambda invocado com evento: {json.dumps(event)}")

    if context:
        logger.info(f"ID da requisição: {context.request_id}")
        logger.info(f"ARN da função: {context.invoked_function_arn}")
        logger.info(f"Tempo restante: {context.get_remaining_time_in_millis()}ms")

    try:
        processing_service = ProcessingService()
        results = []

        for record in event.get("Records", []):
            if record.get("eventSource") == "aws:sqs":
                try:
                    message_body = json.loads(record["body"])
                    result = processing_service.process_message(message_body)
                    results.append(result)
                except Exception as e:
                    logger.exception(f"Erro ao processar mensagem: {e}")
                    results.append({"status": "error", "error": str(e)})

        logger.info(f"Processamento concluído. {len(results)} mensagens processadas")
        
        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "Processamento concluído",
                "processed_count": len(results),
                "results": results,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
        }

    except Exception as e:
        logger.exception(f"Exceção não tratada no handler do Lambda: {e}")

        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": "Erro interno do servidor",
                "message": str(e),
                "requestId": context.request_id if context else None,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
        }