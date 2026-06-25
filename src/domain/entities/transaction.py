"""Transaction domain entity — immutable ledger record."""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum


class TransactionType(str, Enum):
    PAYMENT = "payment"
    PAYROLL = "payroll"
    SPLIT = "split"
    SUBSCRIPTION = "subscription"
    REFUND = "refund"


class TransactionStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    FAILED = "failed"


@dataclass
class Transaction:
    tx_hash: str
    from_address: str
    to_address: str
    amount_usdc: Decimal
    tx_type: TransactionType
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: TransactionStatus = TransactionStatus.PENDING
    invoice_id: str | None = None
    subscription_id: str | None = None
    payroll_run_id: str | None = None
    gas_used: int | None = None
    metadata: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    confirmed_at: datetime | None = None

    def confirm(self, gas_used: int | None = None) -> None:
        self.status = TransactionStatus.CONFIRMED
        self.confirmed_at = datetime.now(timezone.utc)
        if gas_used:
            self.gas_used = gas_used
