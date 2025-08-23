import logging
from typing import Any, Dict, Optional

import aiohttp

logger = logging.getLogger(__name__)


class EC2Client:
    def __init__(self, base_url: str, timeout: int = 30):
        if not base_url:
            raise ValueError("base_url é obrigatório")
            
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.detect_endpoint = f"{self.base_url}/detect"
        self.combined_endpoint = f"{self.base_url}/process-combined"
        logger.info(f"Inicializando cliente EC2 para endpoint {self.base_url}")

    async def _make_request(self, url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=self.timeout) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Erro na resposta da API de IA: {response.status} - {error_text}")
                        return {
                            "status": "error",
                            "error_message": f"Erro {response.status}: {error_text}",
                        }

                    return await response.json()
        except aiohttp.ClientError as e:
            logger.error(f"Erro ao conectar à API de IA: {e}")
            return {"status": "error", "error_message": f"Erro de conexão: {str(e)}"}
        except Exception as e:
            logger.error(f"Erro inesperado ao processar requisição: {e}")
            return {"status": "error", "error_message": f"Erro inesperado: {str(e)}"}

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
