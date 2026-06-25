"""Abstract subscription repository."""

from abc import ABC, abstractmethod
from datetime import datetime

from src.domain.entities.subscription import Subscription, SubscriptionStatus


class AbstractSubscriptionRepository(ABC):
    @abstractmethod
    def save(self, subscription: Subscription) -> Subscription: ...

    @abstractmethod
    def find_by_id(self, sub_id: str) -> Subscription | None: ...

    @abstractmethod
    def find_due(self, before: datetime) -> list[Subscription]: ...

    @abstractmethod
    def find_by_customer(self, customer_address: str) -> list[Subscription]: ...

    @abstractmethod
    def update(self, subscription: Subscription) -> Subscription: ...
