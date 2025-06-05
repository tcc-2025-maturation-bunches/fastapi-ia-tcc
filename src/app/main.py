import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.modules.device_monitoring.controller.device_controller import monitoring_router
from src.modules.ia_integration.controller.combined_controller import combined_router
from src.modules.ia_integration.controller.ia_controller import ia_router
from src.modules.status.controller.status_controller import status_router
from src.modules.storage.controller.storage_controller import storage_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Inicializando API FastAPI em AWS Lambda")
    yield
    logger.info("Encerrando API FastAPI")


app = FastAPI(
    title="IA Detector API",
    description="API para detecção e análise de maturação usando IA",
    version="0.1.0",
    lifespan=lifespan,
)

# Configuração de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ia_router)
app.include_router(combined_router)
app.include_router(monitoring_router)
app.include_router(storage_router)
app.include_router(status_router)


@app.get("/", tags=["Root"])
async def root():
    return {
        "message": "API de IA para Detecção e Maturação de Frutas",
        "docs": "/docs",
        "health": "/health-check",
    }


@app.get("/health-check", tags=["Health Check"])
async def health_check():
    start_time = time.time()
    health_status = "healthy"
    end_time = time.time()
    response_time = round((end_time - start_time) * 1000, 2)

    return {"status": health_status, "response_time_ms": response_time}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("src.app.main:app", host="0.0.0.0", port=8000, reload=True)
