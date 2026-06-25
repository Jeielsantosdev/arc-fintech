"""Use case: cancel a subscription."""

from src.domain.repositories.subscription_repo import AbstractSubscriptionRepository


class CancelSubscriptionUseCase:
    def __init__(self, sub_repo: AbstractSubscriptionRepository) -> None:
        self._repo = sub_repo

    def execute(self, subscription_id: str) -> dict:
        sub = self._repo.find_by_id(subscription_id)
        if not sub:
            raise ValueError(f"Subscription {subscription_id} not found")
        sub.cancel()
        self._repo.update(sub)
        return {
            "subscription_id": sub.id,
            "status": sub.status.value,
            "cancelled_at": sub.cancelled_at.isoformat() if sub.cancelled_at else None,
        }
