"""Split rule domain entity — defines how a payment is divided."""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum


class SplitStatus(str, Enum):
    PENDING = "pending"
    EXECUTING = "executing"
    DONE = "done"
    FAILED = "failed"


@dataclass
class SplitRecipient:
    address: str
    percentage: Decimal
    label: str = ""

    def amount_for(self, total: Decimal) -> Decimal:
        return (total * self.percentage / Decimal("100")).quantize(Decimal("0.000001"))


@dataclass
class SplitRule:
    name: str
    recipients: list[SplitRecipient]
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def validate(self) -> None:
        total = sum(r.percentage for r in self.recipients)
        if abs(total - Decimal("100")) > Decimal("0.01"):
            raise ValueError(f"Split percentages must sum to 100, got {total}")

    def breakdown(self, total_amount: Decimal) -> list[dict]:
        return [
            {
                "address": r.address,
                "label": r.label,
                "percentage": str(r.percentage),
                "amount_usdc": str(r.amount_for(total_amount)),
            }
            for r in self.recipients
        ]


@dataclass
class SplitExecution:
    split_rule_id: str
    invoice_id: str
    total_amount: Decimal
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: SplitStatus = SplitStatus.PENDING
    tx_hashes: list[str] = field(default_factory=list)
    error: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None
