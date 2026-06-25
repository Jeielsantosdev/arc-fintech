"""Abstract wallet repository."""

from abc import ABC, abstractmethod

from src.domain.entities.wallet import Wallet


class AbstractWalletRepository(ABC):
    @abstractmethod
    def save(self, wallet: Wallet) -> Wallet: ...

    @abstractmethod
    def find_by_id(self, wallet_id: str) -> Wallet | None: ...

    @abstractmethod
    def find_by_user_id(self, user_id: str) -> list[Wallet]: ...

    @abstractmethod
    def find_by_address(self, address: str) -> Wallet | None: ...
