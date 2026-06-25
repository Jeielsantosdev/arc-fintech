"""Invoice domain entity — represents a payment request."""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum


class InvoiceStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


@dataclass
class Invoice:
    amount_usdc: Decimal
    recipient_address: str
    idempotency_key: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: InvoiceStatus = InvoiceStatus.PENDING
    tx_hash: str | None = None
    payer_address: str | None = None
    description: str = ""
    metadata: dict = field(default_factory=dict)
    split_rule_id: str | None = None
    subscription_id: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    paid_at: datetime | None = None
    expires_at: datetime | None = None

    def mark_paid(self, tx_hash: str, payer_address: str | None = None) -> None:
        self.status = InvoiceStatus.PAID
        self.tx_hash = tx_hash
        self.paid_at = datetime.now(timezone.utc)
        if payer_address:
            self.payer_address = payer_address

    def is_pending(self) -> bool:
        return self.status == InvoiceStatus.PENDING

    def is_expired(self) -> bool:
        if self.expires_at and datetime.now(timezone.utc) > self.expires_at:
            return True
        return self.status == InvoiceStatus.EXPIRED
