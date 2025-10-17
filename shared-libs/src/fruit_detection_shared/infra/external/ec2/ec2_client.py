import asyncio
import logging
import random
from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional

import aiohttp

logger = logging.getLogger(__name__)


@dataclass
class RetryContext:
    attempt: int
    max_attempts: int
    last_error: Optional[str] = None
    total_wait_time: float = 0


class EC2Client:
    _session: Optional[aiohttp.ClientSession] = None
    _lock = asyncio.Lock()

    def __init__(self, base_url: str, timeout: int = 30):
        if not base_url:
            raise ValueError("base_url é obrigatório")

        self.base_url = base_url.rstrip("/")
        self.timeout = aiohttp.ClientTimeout(total=timeout, connect=10)
        self.combined_endpoint = f"{self.base_url}/process-combined"
        logger.info(f"Inicializando cliente EC2 para endpoint {self.base_url}")

    @classmethod
    async def get_session(cls) -> aiohttp.ClientSession:
        if cls._session is None or cls._session.closed:
            async with cls._lock:
                if cls._session is None or cls._session.closed:
                    connector = aiohttp.TCPConnector(
                        limit=100,
                        limit_per_host=30,
                        ttl_dns_cache=300,
                        keepalive_timeout=60,
                        force_close=False,
                    )
                    cls._session = aiohttp.ClientSession(
                        connector=connector,
                        timeout=aiohttp.ClientTimeout(total=300),
                    )
        return cls._session

    @classmethod
    async def close_session(cls):
        if cls._session and not cls._session.closed:
            await cls._session.close()
            cls._session = None

    def _calculate_backoff(self, attempt: int, base: float = 2.0, max_wait: float = 30.0) -> float:
        wait = min(base**attempt, max_wait)
        jitter = random.uniform(0, wait * 0.1)  # 10% de jitter
        return wait + jitter

    async def _make_request(self, url: str, payload: Dict[str, Any], retry_count: int = 3) -> Dict[str, Any]:
        session = await self.get_session()
        retry_ctx = RetryContext(attempt=0, max_attempts=retry_count)

        for attempt in range(retry_count):
            retry_ctx.attempt = attempt + 1

            try:
                async with session.post(url, json=payload, timeout=self.timeout) as response:
                    if response.status == 200:
                        if attempt > 0:
                            logger.info(
                                f"Requisição bem-sucedida após {attempt + 1} tentativa(s), "
                                f"tempo total de espera: {retry_ctx.total_wait_time:.2f}s"
                            )
                        return await response.json()

                    error_text = await response.text()
                    retry_ctx.last_error = f"HTTP {response.status}: {error_text}"

                    if response.status >= 500 and attempt < retry_count - 1:
                        wait_time = self._calculate_backoff(attempt)
                        retry_ctx.total_wait_time += wait_time
                        logger.warning(
                            f"Tentativa {attempt + 1}/{retry_count} falhou com status {response.status}, "
                            f"aguardando {wait_time:.2f}s antes de retentar"
                        )
                        await asyncio.sleep(wait_time)
                        continue

                    logger.error(f"Falha após {attempt + 1} tentativa(s): {response.status} - {error_text}")
                    return {
                        "status": "error",
                        "error_message": f"Erro {response.status}: {error_text}",
                        "error_code": "IA_SERVICE_ERROR",
                        "retry_info": asdict(retry_ctx),
                    }

            except asyncio.TimeoutError:
                retry_ctx.last_error = "Timeout na requisição"

                if attempt < retry_count - 1:
                    wait_time = self._calculate_backoff(attempt)
                    retry_ctx.total_wait_time += wait_time
                    logger.warning(
                        f"Timeout na tentativa {attempt + 1}/{retry_count}, " f"retentando em {wait_time:.2f}s"
                    )
                    await asyncio.sleep(wait_time)
                    continue

                logger.error(
                    f"Timeout após {retry_count} tentativa(s), tempo total de espera: {retry_ctx.total_wait_time:.2f}s"
                )
                return {
                    "status": "error",
                    "error_message": "Timeout ao processar requisição",
                    "error_code": "TIMEOUT_ERROR",
                    "retry_info": asdict(retry_ctx),
                }

            except aiohttp.ClientError as e:
                retry_ctx.last_error = f"Erro de conexão: {str(e)}"

                if attempt < retry_count - 1:
                    wait_time = self._calculate_backoff(attempt)
                    retry_ctx.total_wait_time += wait_time
                    logger.warning(
                        f"Erro de conexão na tentativa {attempt + 1}/{retry_count}, "
                        f"retentando em {wait_time:.2f}s: {e}"
                    )
                    await asyncio.sleep(wait_time)
                    continue

                logger.error(f"Erro de conexão após {retry_count} tentativa(s): {e}")
                return {
                    "status": "error",
                    "error_message": f"Erro de conexão: {str(e)}",
                    "error_code": "NETWORK_ERROR",
                    "retry_info": asdict(retry_ctx),
                }

        return {
            "status": "error",
            "error_message": f"Falha após {retry_count} tentativa(s)",
            "error_code": "PROCESSING_ERROR",
            "retry_info": asdict(retry_ctx),
        }

    async def process_combined(
        self,
        image_url: str,
        result_upload_url: str,
        maturation_threshold: float = 0.6,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        payload = {
            "image_url": image_url,
            "result_upload_url": result_upload_url,
            "maturation_threshold": maturation_threshold,
            "metadata": metadata or {},
        }

        logger.info(f"Enviando solicitação de processamento combinado para imagem: {image_url}")
        return await self._make_request(self.combined_endpoint, payload)
