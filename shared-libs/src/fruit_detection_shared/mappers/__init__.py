"""
Mappers - Fruit Detection Shared
Mapeadores para conversão entre modelos
"""

from .contract_mapper import ContractResponseMapper
from .request_summary_mapper import RequestSummaryMapper

__all__ = [
    "ContractResponseMapper",
    "RequestSummaryMapper",
]
