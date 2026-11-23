from typing import Literal

from pydantic import BaseModel, Field


class SentinelVerdict(BaseModel):
    confirmed: bool
    severity: Literal["low", "medium", "high"]
    delay_days: int = Field(ge=0)
    location: str
    confidence: float = Field(ge=0, le=1)
    evidence: list[str] = Field(default_factory=list)


class Exposure(BaseModel):
    order_id: int
    customer: str
    sku: str
    product_id: int
    quantity: int
    due_date: str
    days_of_cover: float
    supplier: str
    stockout_days: int


class ImpactReport(BaseModel):
    exposed: bool
    total_orders_at_risk: int
    worst_stockout_days: int
    exposures: list[Exposure]
