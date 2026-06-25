"""Abstract invoice repository."""

from abc import ABC, abstractmethod

from src.domain.entities.invoice import Invoice, InvoiceStatus


class AbstractInvoiceRepository(ABC):
    @abstractmethod
    def save(self, invoice: Invoice) -> Invoice: ...

    @abstractmethod
    def find_by_id(self, invoice_id: str) -> Invoice | None: ...

    @abstractmethod
    def find_by_idempotency_key(self, key: str) -> Invoice | None: ...

    @abstractmethod
    def find_by_status(self, status: InvoiceStatus, limit: int = 100) -> list[Invoice]: ...

    @abstractmethod
    def update(self, invoice: Invoice) -> Invoice: ...
