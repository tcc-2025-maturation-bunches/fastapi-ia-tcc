import asyncio
import json
import logging
from datetime import datetime, timezone

from mangum import Mangum

from src.app.main import app
from src.services.device_service import DeviceService

logger = logging.getLogger()
logger.setLevel(logging.INFO)

handler = Mangum(app, lifespan="auto")


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
        if "Records" in event and event["Records"]:
            for record in event["Records"]:
                if record.get("EventSource") == "aws:sns":
                    return handle_sns_notification(record, context)

        if event.get("source") == "aws.events" and event.get("detail-type") == "Scheduled Event":
            return handle_scheduled_event(event, context)

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


def handle_scheduled_event(event, context):
    try:
        logger.info("Executando verificação de dispositivos offline")

        device_service = DeviceService()

        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        offline_devices = loop.run_until_complete(device_service.check_offline_devices())

        result = {
            "status": "completed",
            "offline_devices_count": len(offline_devices),
            "offline_device_ids": offline_devices,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        logger.info(f"Verificação de dispositivos offline concluída: {len(offline_devices)} dispositivos offline")

        return {
            "statusCode": 200,
            "body": json.dumps(result),
        }

    except Exception as e:
        logger.exception(f"Erro na verificação de dispositivos offline: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps(
                {
                    "error": "Erro na verificação de dispositivos offline",
                    "message": str(e),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            ),
        }


def handle_sns_notification(record, context):
    try:
        sns_message = json.loads(record["Sns"]["Message"])
        logger.info(f"Processando notificação SNS: {sns_message}")

        event_type = sns_message.get("event_type")
        device_id = sns_message.get("device_id")
        request_id = sns_message.get("request_id")
        processing_result = sns_message.get("processing_result", {})

        if event_type != "processing_complete":
            logger.warning(f"Tipo de evento desconhecido: {event_type}, ignorando")
            return {"statusCode": 200, "body": "Event type not supported"}

        if not device_id:
            logger.warning("Notificação SNS sem device_id, ignorando")
            return {"statusCode": 200, "body": "Notification ignored - no device_id"}

        device_service = DeviceService()

        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        success = loop.run_until_complete(device_service.update_device_statistics(device_id, processing_result))

        if success:
            logger.info(f"Estatísticas atualizadas para dispositivo {device_id} via SNS")
        else:
            logger.warning(f"Falha ao atualizar estatísticas para dispositivo {device_id}")

        return {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "status": "processed",
                    "device_id": device_id,
                    "request_id": request_id,
                    "success": success,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            ),
        }

    except Exception as e:
        logger.exception(f"Erro ao processar notificação SNS: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps(
                {
                    "error": "Erro ao processar notificação SNS",
                    "message": str(e),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            ),
        }
