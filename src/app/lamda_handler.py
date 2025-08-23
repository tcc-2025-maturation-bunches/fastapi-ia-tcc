import json
import logging

from mangum import Mangum

from .main import app

logger = logging.getLogger()
logger.setLevel(logging.INFO)

handler = Mangum(app, lifespan="off")


def lambda_handler(event, context):
    logger.info(f"Evento recebido: {json.dumps(event)}")
    return handler(event, context)
