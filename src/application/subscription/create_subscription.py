"""Use case: create a recurring subscription."""

import logging
from datetime import datetime, timezone
from decimal import Decimal

from src.domain.entities.subscription import Subscription
from src.domain.repositories.subscription_repo import AbstractSubscriptionRepository

logger = logging.getLogger(__name__)


class CreateSubscriptionUseCase:
    def __init__(self, sub_repo: AbstractSubscriptionRepository) -> None:
        self._repo = sub_repo

    def execute(
        self,
        customer_address: str,
        merchant_address: str,
        amount_usdc: Decimal,
        interval_days: int = 30,
        description: str = "",
        split_rule_id: str | None = None,
        metadata: dict | None = None,
        first_due_now: bool = True,
    ) -> dict:
        sub = Subscription(
            customer_address=customer_address,
            merchant_address=merchant_address,
            amount_usdc=amount_usdc,
            interval_days=interval_days,
            description=description,
            split_rule_id=split_rule_id,
            metadata=metadata or {},
            next_due_at=datetime.now(timezone.utc) if first_due_now else
                        datetime.now(timezone.utc),
        )
        saved = self._repo.save(sub)
        logger.info("Subscription created: %s | %s USDC every %d days", saved.id, amount_usdc, interval_days)
        return {
            "subscription_id": saved.id,
            "customer_address": customer_address,
            "merchant_address": merchant_address,
            "amount_usdc": str(amount_usdc),
            "interval_days": interval_days,
            "status": saved.status.value,
            "next_due_at": saved.next_due_at.isoformat(),
        }
