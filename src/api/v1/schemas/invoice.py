"""Invoice / checkout API schemas."""

from decimal import Decimal

from pydantic import BaseModel, Field, field_validator


class CreateInvoiceRequest(BaseModel):
    amount_usdc: Decimal = Field(..., gt=0, description="Amount in USDC")
    recipient_address: str = Field(..., min_length=42, max_length=42)
    description: str = Field("", max_length=500)
    idempotency_key: str | None = None
    split_rule_id: str | None = None
    subscription_id: str | None = None
    expires_in_hours: int = Field(24, ge=1, le=720)
    metadata: dict = Field(default_factory=dict)

    @field_validator("recipient_address")
    @classmethod
    def validate_address(cls, v: str) -> str:
        if not v.startswith("0x"):
            raise ValueError("Address must start with 0x")
        return v


class InvoiceResponse(BaseModel):
    invoice_id: str
    idempotency_key: str
    amount_usdc: str
    recipient_address: str
    status: str
    description: str
    expires_at: str | None
    checkout_url: str
    qr_data: str


class CheckoutRequest(BaseModel):
    invoice_id: str
    idempotency_key: str | None = None
    webhook_url: str | None = None


class CheckoutResponse(BaseModel):
    status: str
    invoice_id: str
    tx_hash: str
    amount_usdc: str
    split: dict | None = None
