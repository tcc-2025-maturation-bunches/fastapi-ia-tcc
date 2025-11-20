import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.app.config import settings
from src.routes.auth_routes import auth_router
from src.routes.user_routes import user_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Inicializando Auth Lambda")
    logger.info(f"Ambiente: {settings.ENVIRONMENT}")
    logger.info(f"Região AWS: {settings.AWS_REGION}")
    logger.info(f"Tabela DynamoDB: {settings.DYNAMODB_TABLE_NAME}")
    logger.info(f"Algoritmo JWT: {settings.JWT_ALGORITHM}")
    yield
    logger.info("Encerrando Auth Lambda")


app = FastAPI(
    title="Auth Lambda",
    description="Lambda responsável por autenticação de usuários e emissão de JWT",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if not settings.is_production() else None,
    redoc_url="/redoc" if not settings.is_production() else None,
    redirect_slashes=False,
    root_path=f"/{settings.ENVIRONMENT}" if not settings.is_development() else None,
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
    logger.info(f"{request.method} {request.url.path} {response.status_code} - {process_time:.3f}s")

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


app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
app.include_router(user_router, prefix="/users", tags=["User Management"])


@app.get("/", tags=["Root"])
async def root():
    return {
        "service": "Auth Lambda",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
        "status": "operational",
        "endpoints": {
            "health": "/health",
            "auth_login": "/auth/login",
            "auth_verify": "/auth/verify",
            "auth_me": "/auth/me",
            "users": "/users",
            "docs": "/docs" if not settings.is_production() else "disabled",
        },
        "features": [
            "Autenticação JWT",
            "Gerenciamento de usuários",
            "Validação de tokens",
            "Controle de acesso",
        ],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/health", tags=["Health"])
async def health():
    return {
        "status": "ok",
        "service": settings.SERVICE_NAME,
        "version": settings.SERVICE_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/info", tags=["Informações"])
async def info():
    return {
        "service": "Auth Lambda",
        "version": "1.0.0",
        "description": "Lambda responsável por autenticação de usuários e emissão de JWT",
        "environment": settings.ENVIRONMENT,
        "aws_region": settings.AWS_REGION,
        "configuration": {
            "jwt_algorithm": settings.JWT_ALGORITHM,
            "access_token_expire_minutes": settings.ACCESS_TOKEN_EXPIRE_MINUTES,
        },
        "integrations": {
            "dynamodb_table": settings.DYNAMODB_TABLE_NAME,
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
