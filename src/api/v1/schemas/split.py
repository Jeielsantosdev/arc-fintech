"""Split payment API schemas."""

from decimal import Decimal

from pydantic import BaseModel, Field


class SplitRecipientInput(BaseModel):
    address: str = Field(..., min_length=42, max_length=42)
    percentage: Decimal = Field(..., gt=0, le=100)
    label: str = ""


class CreateSplitRequest(BaseModel):
    name: str = Field(..., min_length=1)
    recipients: list[SplitRecipientInput] = Field(..., min_length=2)
    total_amount_usdc: Decimal = Field(..., gt=0)
    invoice_id: str | None = None
    broadcast: bool = True


class SplitResponse(BaseModel):
    split_rule_id: str
    name: str
    status: str
    tx_hashes: list[str]
    breakdown: list[dict]
