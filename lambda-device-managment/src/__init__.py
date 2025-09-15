"""
Device Management Lambda - Source Package
Pacote principal contendo todos os módulos da aplicação Lambda.

Estrutura:
- app/: Configuração principal e handlers
- repository/: Camada de acesso a dados (DynamoDB)
- routes/: Definição de endpoints da API
- services/: Lógica de negócio
- utils/: Utilitários e validadores
"""

__version__ = "1.0.0"
__package_name__ = "device-management-lambda-src"

from .app import app, settings, lambda_handler

__all__ = [
    "app",
    "settings",
    "lambda_handler",
    "__version__"
]