from typing import List, Optional

from pydantic import BaseModel


class MaturationDistributionItem(BaseModel):
    name: str
    value: int
    color: Optional[str] = None


class MaturationTrendItem(BaseModel):
    date: str
    verde: int
    quase_maduro: int
    maduro: int
    muito_maduro_ou_passado: int
    total: int


class LocationCountItem(BaseModel):
    location: str
    count: int
    verde: int
    quase_maduro: int
    maduro: int
    muito_maduro_ou_passado: int


class InferenceStatsResponse(BaseModel):
    period_days: int
    total_inspections: int
    total_objects_detected: int
    maturation_distribution: List[MaturationDistributionItem]
    maturation_trend: List[MaturationTrendItem]
    counts_by_location: List[LocationCountItem]
    generated_at: str
