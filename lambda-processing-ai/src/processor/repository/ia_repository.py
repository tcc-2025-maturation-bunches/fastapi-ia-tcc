import logging
from typing import Any, Dict, Optional

from fruit_detection_shared.domain.entities import Image
from fruit_detection_shared.infra.external import EC2Client

from src.app.config import settings

logger = logging.getLogger(__name__)


class IARepository:
    def __init__(self, ec2_client: Optional[EC2Client] = None):
        self.ec2_client = ec2_client or EC2Client(base_url=settings.EC2_IA_ENDPOINT, timeout=settings.REQUEST_TIMEOUT)

    async def request_combined_processing(
        self,
        image: Image,
        result_upload_url: Optional[str],
        maturation_threshold: float = 0.6,
    ) -> Dict[str, Any]:
        metadata = {
            **(image.metadata or {}),
            "user_id": image.user_id,
            "image_id": image.image_id,
            "timestamp": image.upload_timestamp.isoformat(),
        }

        try:
            response = await self.ec2_client.process_combined(
                image_url=image.image_url,
                result_upload_url=result_upload_url,
                maturation_threshold=maturation_threshold,
                metadata=metadata,
            )

            logger.info(f"Resposta recebida do EC2 para imagem: {image.image_id}")
            return response

        except Exception as e:
            logger.exception(f"Erro ao comunicar com serviço EC2: {e}")
            return {
                "status": "error",
                "error_message": f"Erro de comunicação: {str(e)}",
                "error_code": "NETWORK_ERROR",
            }

    async def health_check(self) -> bool:
        try:
            import aiohttp

            health_url = f"{self.ec2_client.base_url}/health"

            async with aiohttp.ClientSession() as session:
                async with session.get(health_url, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        is_healthy = data.get("status") == "healthy"

                        if is_healthy:
                            logger.info("Serviço de IA está saudável")
                        else:
                            logger.warning("Serviço de IA reportou status não saudável")

                        return is_healthy

                    logger.error(f"Health check retornou status {response.status}")
                    return False

        except Exception as e:
            logger.error(f"Erro ao verificar health do serviço de IA: {e}")
            return False
