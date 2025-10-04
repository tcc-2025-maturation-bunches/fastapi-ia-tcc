import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.app.config import settings
from src.routes import device_router, health_router
from src.utils.validators import validate_device_id

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Inicializando Device Management Lambda")
    logger.info(f"Ambiente: {settings.ENVIRONMENT}")
    logger.info(f"Região AWS: {settings.AWS_REGION}")
    logger.info(f"Tabela DynamoDB: {settings.DYNAMODB_TABLE_NAME}")
    logger.info(f"Timeout de heartbeat: {settings.HEARTBEAT_TIMEOUT_MINUTES} minutos")
    yield
    logger.info("Encerrando Device Management Lambda")


app = FastAPI(
    title="Device Management Lambda",
    description="Lambda para gerenciamento de dispositivos Raspberry Pi no sistema de detecção de frutas",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if not settings.is_production() else None,
    redoc_url="/redoc" if not settings.is_production() else None,
    redirect_slashes=False,
    root_path=f"/{settings.ENVIRONMENT}" if not settings.is_development() else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    response.headers["X-Environment"] = settings.ENVIRONMENT
    response.headers["X-Service"] = settings.SERVICE_NAME
    return response


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()

    logger.info(
        f"Requisição: {request.method} {request.url.path} "
        f"- User-Agent: {request.headers.get('user-agent', 'unknown')}"
    )
    response = await call_next(request)

    process_time = time.time() - start_time
    logger.info(
        f"Resposta: {request.method} {request.url.path} "
        f"- Status: {response.status_code} "
        f"- Tempo: {process_time:.3f}s"
    )

    return response


DEVICE_SPECIAL_ENDPOINTS = ["all", "register", "global-config", "stats"]
VALID_DEVICE_ACTIONS = ["heartbeat", "config", "processing-notification"]

@app.middleware("http")
async def validate_device_path_params(request: Request, call_next):
    path = str(request.url.path)

    if "/devices/" in path:
        path_parts = path.split("/")

        try:
            device_index = path_parts.index("devices")

            if device_index + 1 < len(path_parts):
                device_id_segment = path_parts[device_index + 1]

                if not device_id_segment:
                    return JSONResponse(status_code=400, content={"detail": "Device ID is missing or invalid in path."})
                if device_id_segment in DEVICE_SPECIAL_ENDPOINTS:
                    response = await call_next(request)
                    return response

                if device_index + 2 < len(path_parts):
                    action = path_parts[device_index + 2]
                    if action in VALID_DEVICE_ACTIONS:
                        try:
                            validate_device_id(device_id_segment)
                        except HTTPException as e:
                            logger.warning(f"Validation failed for device_id: {device_id_segment}")
                            return JSONResponse(status_code=e.status_code, content={"detail": e.detail})
                else:
                    try:
                        validate_device_id(device_id_segment)
                    except HTTPException as e:
                        logger.warning(f"Validation failed for device_id: {device_id_segment}")
                        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})

        except (ValueError, IndexError) as e:
            logger.warning(f"Malformed device path: {path} - {e}")
            return JSONResponse(status_code=400, content={"detail": "Malformed device path or missing device ID."})

    response = await call_next(request)
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Exceção não tratada: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Erro interno do servidor",
            "message": "Ocorreu um erro inesperado",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "path": str(request.url.path),
        },
    )


app.include_router(health_router, prefix="/health", tags=["Health"])
app.include_router(device_router, prefix="/devices", tags=["Device Management"])


@app.get("/", tags=["Root"])
async def root():
    return {
        "service": "Device Management Lambda",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
        "status": "operational",
        "endpoints": {
            "health": "/health",
            "health_detailed": "/health/detailed",
            "device_register": "/devices/register",
            "device_heartbeat": "/devices/{device_id}/heartbeat",
            "device_config": "/devices/{device_id}/config",
            "device_list": "/devices/all",
            "device_stats": "/devices/stats",
            "docs": "/docs" if not settings.is_production() else "disabled",
        },
        "features": [
            "Registro de dispositivos Raspberry Pi",
            "Monitoramento de heartbeat",
            "Gerenciamento de configuração",
            "Rastreamento de estatísticas",
            "Detecção automática de dispositivos offline",
        ],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/info", tags=["Informações"])
async def info():
    return {
        "service": "Device Management Lambda",
        "version": "1.0.0",
        "description": "Gerencia o ciclo de vida de dispositivos Raspberry Pi",
        "environment": settings.ENVIRONMENT,
        "aws_region": settings.AWS_REGION,
        "configuration": {
            "heartbeat_timeout_minutes": settings.HEARTBEAT_TIMEOUT_MINUTES,
            "offline_check_interval_minutes": settings.OFFLINE_CHECK_INTERVAL_MINUTES,
            "default_capture_interval": settings.DEFAULT_CAPTURE_INTERVAL,
            "default_image_quality": settings.DEFAULT_IMAGE_QUALITY,
            "default_heartbeat_interval": settings.DEFAULT_HEARTBEAT_INTERVAL,
        },
        "integrations": {
            "dynamodb_table": settings.DYNAMODB_TABLE_NAME,
            "sns_topic": settings.SNS_PROCESSING_COMPLETE_TOPIC,
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
