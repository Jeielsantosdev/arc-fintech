"""Subscription domain entity — recurring payments."""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from enum import Enum


class SubscriptionStatus(str, Enum):
    ACTIVE = "active"
    CANCELLED = "cancelled"
    SUSPENDED = "suspended"
    PAST_DUE = "past_due"


@dataclass
class Subscription:
    customer_address: str
    merchant_address: str
    amount_usdc: Decimal
    interval_days: int
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: SubscriptionStatus = SubscriptionStatus.ACTIVE
    retry_count: int = 0
    max_retries: int = 3
    split_rule_id: str | None = None
    description: str = ""
    metadata: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    next_due_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    cancelled_at: datetime | None = None
    last_paid_at: datetime | None = None

    def renew(self) -> None:
        """Advance the next due date by one interval."""
        self.next_due_at = datetime.now(timezone.utc) + timedelta(days=self.interval_days)
        self.last_paid_at = datetime.now(timezone.utc)
        self.retry_count = 0
        self.status = SubscriptionStatus.ACTIVE

    def record_failure(self) -> None:
        self.retry_count += 1
        if self.retry_count >= self.max_retries:
            self.status = SubscriptionStatus.SUSPENDED
        else:
            self.status = SubscriptionStatus.PAST_DUE

    def cancel(self) -> None:
        self.status = SubscriptionStatus.CANCELLED
        self.cancelled_at = datetime.now(timezone.utc)

    def is_due(self) -> bool:
        return (
            self.status in (SubscriptionStatus.ACTIVE, SubscriptionStatus.PAST_DUE)
            and datetime.now(timezone.utc) >= self.next_due_at
        )
