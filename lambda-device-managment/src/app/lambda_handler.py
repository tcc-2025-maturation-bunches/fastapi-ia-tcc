import json
import logging
from datetime import datetime, timezone

from mangum import Mangum

from src.app.main import app

logger = logging.getLogger()
logger.setLevel(logging.INFO)

handler = Mangum(app, lifespan="off")


def lambda_handler(event, context):
    event_str = json.dumps(event, default=str)
    if len(event_str) > 1000:
        logger.info(f"Lambda invocado - Evento (truncado): {event_str[:1000]}...")
    else:
        logger.info(f"Lambda invocado - Evento: {event_str}")

    if context:
        logger.info(f"ID da requisição: {context.aws_request_id}")
        logger.info(f"ARN da função: {context.invoked_function_arn}")
        logger.info(f"Tempo restante: {context.get_remaining_time_in_millis()}ms")

    try:
        response = handler(event, context)
        logger.info(f"Execução do Lambda bem-sucedida. Status: {response.get('statusCode', 'desconhecido')}")

        return response

    except Exception as e:
        logger.exception(f"Exceção não tratada no handler do Lambda: {e}")

        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
            "body": json.dumps(
                {
                    "error": "Erro interno do servidor",
                    "message": str(e),
                    "requestId": context.aws_request_id if context else None,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            ),
        }
