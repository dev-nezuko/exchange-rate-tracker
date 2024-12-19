from datetime import date, datetime, timezone
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ExchangeRate(BaseModel):
    id: int
    currency: str
    rate: float
    change: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)


class ExchangeRateResponse(BaseModel):
    Date: date = Field(default_factory=lambda: datetime.now(timezone.utc).date())
    rates: List[ExchangeRate]
