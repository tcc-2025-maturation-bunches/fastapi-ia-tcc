from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, field_validator, model_validator


class DateRangeFilter(BaseModel):
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

    @field_validator("start_date", "end_date")
    @classmethod
    def ensure_timezone_aware(cls, v: Optional[datetime]) -> Optional[datetime]:
        if v is not None and v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v

    @model_validator(mode="after")
    def validate_date_range(self) -> "DateRangeFilter":
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValueError("start_date cannot be after end_date")
        return self
