import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Inicializando Request Handler Lambda")
    yield
    logger.info("Encerrando Request Handler Lambda")


app = FastAPI(
    title="Request Handler Lambda",
    description="Lambda para integração com API Gateway do sistema de detecção de frutas",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
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
        },
    )


@app.get("/", tags=["Root"])
async def root():
    return {
        "service": "Request Handler Lambda",
        "status": "operational",
        "endpoints": {
            "health": "/health",
            "storage": "/storage",
            "processing": "/combined",
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/info", tags=["Informações"])
async def info():
    return {
        "service": "Request Handler Lambda",
        "version": "1.0.0",
        "description": "Processa requisições de entrada e orquestra o processamento",
        "features": [
            "Geração de URLs pré-assinadas",
            "Processamento assíncrono via SQS",
            "Rastreamento de status de processamento",
            "Monitoramento de saúde",
        ],
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
