import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.app.config import settings
from src.routes import health_router, results_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Inicializando Results Query Lambda")
    logger.info(f"Ambiente: {settings.ENVIRONMENT}")
    logger.info(f"Região AWS: {settings.AWS_REGION}")
    logger.info(f"Tabela DynamoDB: {settings.DYNAMODB_TABLE_NAME}")
    logger.info(f"Bucket de Resultados: {settings.S3_RESULTS_BUCKET}")
    yield
    logger.info("Encerrando Results Query Lambda")


app = FastAPI(
    title="Results Query Lambda",
    description="Lambda para consulta de resultados do sistema de detecção de frutas",
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
app.include_router(results_router, prefix="/results", tags=["Results"])


@app.get("/", tags=["Root"])
async def root():
    return {
        "service": "Results Query Lambda",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
        "status": "operational",
        "endpoints": {
            "health": "/health",
            "results": "/results",
            "docs": "/docs" if not settings.is_production() else "disabled",
        },
        "features": [
            "Consulta de resultados por request_id",
            "Consulta de resultados por image_id",
            "Consulta de resultados por user_id",
            "Listagem de todos os resultados",
            "Paginação e filtros avançados",
            "Sumários e relatórios",
        ],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
