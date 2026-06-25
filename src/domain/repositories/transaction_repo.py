"""Abstract transaction repository."""

from abc import ABC, abstractmethod

from src.domain.entities.transaction import Transaction


class AbstractTransactionRepository(ABC):
    @abstractmethod
    def save(self, tx: Transaction) -> Transaction: ...

    @abstractmethod
    def find_by_id(self, tx_id: str) -> Transaction | None: ...

    @abstractmethod
    def find_by_tx_hash(self, tx_hash: str) -> Transaction | None: ...

    @abstractmethod
    def find_by_address(
        self, address: str, limit: int = 50, offset: int = 0
    ) -> list[Transaction]: ...

    @abstractmethod
    def update(self, tx: Transaction) -> Transaction: ...
