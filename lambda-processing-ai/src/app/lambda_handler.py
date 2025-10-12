import json
import logging
from datetime import datetime, timezone

from src.app.config import settings
from src.processor.processing_service import ProcessingService

logger = logging.getLogger()
logger.setLevel(getattr(logging, settings.LOG_LEVEL))


def lambda_handler(event, context):
    logger.info("=== Lambda Processing AI Iniciada ===")
    logger.info(f"Versão: {settings.SERVICE_VERSION}")
    logger.info(f"Ambiente: {settings.ENVIRONMENT}")
    logger.info(f"Região: {settings.AWS_REGION}")
    logger.info(f"EC2 IA Endpoint: {settings.EC2_IA_ENDPOINT}")
    logger.info(f"DynamoDB Table: {settings.DYNAMODB_TABLE_NAME}")

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
            logger.info("ProcessingService inicializado com sucesso")
        except ValueError as e:
            logger.error(f"Erro de configuração ao inicializar ProcessingService: {e}")
            return {
                "statusCode": 500,
                "body": json.dumps(
                    {
                        "error": "Configuração inválida",
                        "message": str(e),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                ),
            }
        except Exception as e:
            logger.exception(f"Erro inesperado ao inicializar ProcessingService: {e}")
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

        results = []
        failed_messages = []

        for record in event["Records"]:
            if record.get("eventSource") == "aws:sqs":
                message_id = record.get("messageId", "unknown")
                try:
                    logger.info(f"Processando mensagem SQS: {message_id}")
                    message_body = json.loads(record["body"])

                    result = processing_service.process_message(message_body)
                    results.append(result)

                    logger.info(f"Mensagem {message_id} processada com sucesso")

                except json.JSONDecodeError as e:
                    logger.error(f"Erro ao decodificar JSON da mensagem {message_id}: {e}")
                    failed_messages.append(
                        {
                            "message_id": message_id,
                            "error": "Invalid JSON",
                            "details": str(e),
                        }
                    )

                except Exception as e:
                    logger.exception(f"Erro ao processar mensagem {message_id}: {e}")
                    failed_messages.append(
                        {
                            "message_id": message_id,
                            "error": str(e),
                            "request_id": message_body.get("request_id") if "message_body" in locals() else None,
                        }
                    )

        success_count = len(results)
        failed_count = len(failed_messages)

        logger.info(f"Processamento concluído - Sucesso: {success_count}, Falhas: {failed_count}")

        return {
            "statusCode": 200 if failed_count == 0 else 207,
            "body": json.dumps(
                {
                    "message": "Processamento concluído",
                    "processed_count": success_count,
                    "failed_count": failed_count,
                    "results": results,
                    "failed_messages": failed_messages if failed_messages else None,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
                default=str,
            ),
        }

    except Exception as e:
        logger.exception(f"Exceção não tratada no handler do Lambda: {e}")

        return {
            "statusCode": 500,
            "body": json.dumps(
                {
                    "error": "Erro interno do servidor",
                    "message": str(e),
                    "requestId": context.aws_request_id if context else None,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
                default=str,
            ),
        }
