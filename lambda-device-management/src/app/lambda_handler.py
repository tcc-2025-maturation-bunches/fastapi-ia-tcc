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


def lambda_handler(event: dict, context: object) -> dict:
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
        if event.get("source") == "aws.events":
            logger.info("Evento agendado detectado. Iniciando verificação de dispositivos offline.")
            return asyncio.get_event_loop().run_until_complete(handle_scheduled_event(event, context))

        if "Records" in event and event["Records"]:
            record = event["Records"][0]
            if record.get("EventSource") == "aws:sns":
                logger.info("Evento do SNS detectado. Processando notificação.")
                return asyncio.get_event_loop().run_until_complete(handle_sns_notification(record, context))

        logger.info("Nenhum evento especial detectado. Repassando para o handler da API Gateway (Mangum).")
        response = handler(event, context)
        logger.info(
            f"Execução do Lambda (API Gateway) bem-sucedida. Status: {response.get('statusCode', 'desconhecido')}"
        )
        return response

    except Exception as e:
        logger.exception(f"Exceção não tratada no handler do Lambda: {e}")
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "Erro interno do servidor", "message": str(e)}),
        }


async def handle_scheduled_event(event: dict, context: object) -> dict:
    try:
        device_service = DeviceService()
        offline_devices = await device_service.check_offline_devices()

        result = {
            "status": "completed",
            "offline_devices_count": len(offline_devices),
            "offline_device_ids": offline_devices,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        logger.info(f"Verificação de dispositivos offline concluída: {len(offline_devices)} dispositivos offline.")
        return {"statusCode": 200, "body": json.dumps(result)}

    except Exception as e:
        logger.exception(f"Erro na verificação de dispositivos offline: {e}")
        return {"statusCode": 500, "body": json.dumps({"error": "Erro na verificação", "message": str(e)})}


async def handle_sns_notification(record: dict, context: object) -> dict:
    try:
        sns_message = json.loads(record["Sns"]["Message"])
        logger.info(f"Processando notificação SNS: {sns_message}")

        device_id = sns_message.get("device_id")
        processing_result = sns_message.get("processing_result", {})

        if sns_message.get("event_type") != "processing_complete":
            logger.warning(f"Tipo de evento SNS desconhecido: {sns_message.get('event_type')}, ignorando.")
            return {"statusCode": 200, "body": json.dumps({"status": "ignored", "reason": "Event type not supported"})}

        if not device_id:
            logger.warning("Notificação SNS sem device_id, ignorando.")
            return {"statusCode": 200, "body": json.dumps({"status": "ignored", "reason": "No device_id found"})}

        device_service = DeviceService()
        success = await device_service.update_device_statistics(device_id, processing_result)

        if success:
            logger.info(f"Estatísticas atualizadas para dispositivo {device_id} via SNS.")
        else:
            logger.warning(f"Falha ao atualizar estatísticas para dispositivo {device_id}.")

        return {"statusCode": 200, "body": json.dumps({"status": "processed", "success": success})}

    except Exception as e:
        logger.exception(f"Erro ao processar notificação SNS: {e}")
        return {"statusCode": 500, "body": json.dumps({"error": "Erro ao processar SNS", "message": str(e)})}
