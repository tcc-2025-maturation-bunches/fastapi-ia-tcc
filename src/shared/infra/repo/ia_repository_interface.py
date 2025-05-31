from abc import ABC, abstractmethod

from ...domain.entities.image import Image
from ...domain.entities.result import ProcessingResult


class IARepositoryInterface(ABC):
    """Interface para o repositório de IA."""

    @abstractmethod
    async def detect_objects(self, image: Image, result_upload_url: str) -> ProcessingResult:
        """
        Detecta objetos em uma imagem.

        Args:
            image: Entidade de imagem com URL e metadados
            result_upload_url: URL pré-assinada para upload do resultado

        Returns:
            ProcessingResult: Resultado do processamento com detecções
        """
        pass

    @abstractmethod
    async def process_combined(
        self, image: Image, result_upload_url: str, maturation_threshold: float = 0.6
    ) -> ProcessingResult:
        """
        Processa uma imagem com detecção e análise de maturação combinadas.

        Args:
            image: Entidade de imagem com URL e metadados
            result_upload_url: URL pré-assinada para upload do resultado
            maturation_threshold: Limiar de confiança para análise de maturação

        Returns:
            ProcessingResult: Resultado do processamento combinado
        """
        pass
