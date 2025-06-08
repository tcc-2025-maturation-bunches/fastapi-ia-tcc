from enum import Enum


class ModelType(str, Enum):
    """Modelos de IA disponíveis."""

    DETECTION = "detection"
    COMBINED = "combined"
