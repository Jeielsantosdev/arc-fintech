"""Concrete SQLAlchemy subscription repository."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from src.domain.entities.subscription import Subscription, SubscriptionStatus
from src.domain.repositories.subscription_repo import AbstractSubscriptionRepository
from src.infrastructure.database.models.subscription import SubscriptionModel


def _to_entity(m: SubscriptionModel) -> Subscription:
    return Subscription(
        id=m.id,
        customer_address=m.customer_address,
        merchant_address=m.merchant_address,
        amount_usdc=Decimal(str(m.amount_usdc)),
        interval_days=m.interval_days,
        status=SubscriptionStatus(m.status),
        retry_count=m.retry_count,
        max_retries=m.max_retries,
        split_rule_id=m.split_rule_id,
        description=m.description,
        metadata=m.metadata_ or {},
        created_at=m.created_at,
        next_due_at=m.next_due_at,
        cancelled_at=m.cancelled_at,
        last_paid_at=m.last_paid_at,
    )


class SqlSubscriptionRepository(AbstractSubscriptionRepository):
    def __init__(self, db: Session) -> None:
        self._db = db

    def save(self, sub: Subscription) -> Subscription:
        m = SubscriptionModel(
            id=sub.id,
            customer_address=sub.customer_address,
            merchant_address=sub.merchant_address,
            amount_usdc=float(sub.amount_usdc),
            interval_days=sub.interval_days,
            status=sub.status.value,
            retry_count=sub.retry_count,
            max_retries=sub.max_retries,
            split_rule_id=sub.split_rule_id,
            description=sub.description,
            metadata_=sub.metadata,
            next_due_at=sub.next_due_at,
        )
        self._db.add(m)
        self._db.commit()
        self._db.refresh(m)
        return _to_entity(m)

    def find_by_id(self, sub_id: str) -> Subscription | None:
        m = self._db.get(SubscriptionModel, sub_id)
        return _to_entity(m) if m else None

    def find_due(self, before: datetime) -> list[Subscription]:
        rows = (
            self._db.query(SubscriptionModel)
            .filter(
                SubscriptionModel.next_due_at <= before,
                SubscriptionModel.status.in_(["active", "past_due"]),
            )
            .all()
        )
        return [_to_entity(r) for r in rows]

    def find_by_customer(self, customer_address: str) -> list[Subscription]:
        rows = (
            self._db.query(SubscriptionModel)
            .filter_by(customer_address=customer_address)
            .all()
        )
        return [_to_entity(r) for r in rows]

    def update(self, sub: Subscription) -> Subscription:
        m = self._db.get(SubscriptionModel, sub.id)
        if not m:
            raise ValueError(f"Subscription {sub.id} not found")
        m.status = sub.status.value
        m.retry_count = sub.retry_count
        m.next_due_at = sub.next_due_at
        m.last_paid_at = sub.last_paid_at
        m.cancelled_at = sub.cancelled_at
        m.metadata_ = sub.metadata
        self._db.commit()
        self._db.refresh(m)
        return _to_entity(m)
