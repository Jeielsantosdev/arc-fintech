"""Subscription API schemas."""

from decimal import Decimal

from pydantic import BaseModel, Field


class CreateSubscriptionRequest(BaseModel):
    customer_address: str = Field(..., min_length=42, max_length=42)
    merchant_address: str = Field(..., min_length=42, max_length=42)
    amount_usdc: Decimal = Field(..., gt=0)
    interval_days: int = Field(30, ge=1, le=365)
    description: str = ""
    split_rule_id: str | None = None
    metadata: dict = Field(default_factory=dict)


class SubscriptionResponse(BaseModel):
    subscription_id: str
    customer_address: str
    merchant_address: str
    amount_usdc: str
    interval_days: int
    status: str
    next_due_at: str


class CancelSubscriptionResponse(BaseModel):
    subscription_id: str
    status: str
    cancelled_at: str | None
