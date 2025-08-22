import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.app.config import settings
from src.routes import combined_router, health_router, storage_router
from src.utils.validators import validate_request_id, validate_user_id

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Inicializando Request Handler Lambda")
    logger.info(f"Ambiente: {settings.ENVIRONMENT}")
    logger.info(f"Região AWS: {settings.AWS_REGION}")
    logger.info(f"Fila SQS: {settings.SQS_QUEUE_URL}")
    logger.info(f"Tabela DynamoDB: {settings.DYNAMODB_TABLE_NAME}")
    logger.info(f"Bucket de Imagens: {settings.S3_IMAGES_BUCKET}")
    logger.info(f"Bucket de Resultados: {settings.S3_RESULTS_BUCKET}")
    yield
    logger.info("Encerrando Request Handler Lambda")


app = FastAPI(
    title="Request Handler Lambda",
    description="Lambda para integração com API Gateway do sistema de detecção de frutas",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if not settings.is_production() else None,
    redoc_url="/redoc" if not settings.is_production() else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=settings.CORS_METHODS,
    allow_headers=settings.CORS_HEADERS,
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


@app.middleware("http")
async def validate_path_params(request: Request, call_next):
    if "/user/" in str(request.url.path):
        path_parts = str(request.url.path).split("/")
        if "user" in path_parts:
            user_index = path_parts.index("user")
            if user_index + 1 < len(path_parts):
                user_id = path_parts[user_index + 1]
                try:
                    validate_user_id(user_id)
                except HTTPException as e:
                    return JSONResponse(status_code=e.status_code, content={"detail": e.detail})

    if "/status/" in str(request.url.path):
        path_parts = str(request.url.path).split("/")
        if "status" in path_parts:
            status_index = path_parts.index("status")
            if status_index + 1 < len(path_parts):
                request_id = path_parts[status_index + 1]
                try:
                    validate_request_id(request_id)
                except HTTPException as e:
                    return JSONResponse(status_code=e.status_code, content={"detail": e.detail})

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
app.include_router(storage_router, prefix="/storage", tags=["Storage"])
app.include_router(combined_router, prefix="/combined", tags=["Combined Processing"])


@app.get("/", tags=["Root"])
async def root():
    return {
        "service": "Request Handler Lambda",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
        "status": "operational",
        "endpoints": {
            "health": "/health",
            "health_detailed": "/health/detailed",
            "storage": "/storage",
            "processing": "/combined",
            "docs": "/docs" if not settings.is_production() else "disabled",
        },
        "features": [
            "Geração de URLs pré-assinadas",
            "Processamento assíncrono via SQS",
            "Rastreamento de status de processamento",
            "Monitoramento de saúde",
            "Processamento em lote",
        ],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/info", tags=["Informações"])
async def info():
    return {
        "service": "Request Handler Lambda",
        "version": "1.0.0",
        "description": "Processa requisições de entrada e orquestra o processamento",
        "environment": settings.ENVIRONMENT,
        "aws_region": settings.AWS_REGION,
        "configuration": {
            "presigned_url_expiry_minutes": settings.PRESIGNED_URL_EXPIRY_MINUTES,
            "max_upload_size_mb": settings.MAX_UPLOAD_SIZE_MB,
            "allowed_image_types": settings.ALLOWED_IMAGE_TYPES,
            "min_detection_confidence": settings.MIN_DETECTION_CONFIDENCE,
            "min_maturation_confidence": settings.MIN_MATURATION_CONFIDENCE,
            "processing_timeout_seconds": settings.PROCESSING_TIMEOUT_SECONDS,
            "rate_limit_per_minute": settings.RATE_LIMIT_PER_MINUTE,
        },
        "integrations": {
            "sqs_queue": settings.SQS_QUEUE_URL,
            "dynamodb_table": settings.DYNAMODB_TABLE_NAME,
            "s3_images_bucket": settings.S3_IMAGES_BUCKET,
            "s3_results_bucket": settings.S3_RESULTS_BUCKET,
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
