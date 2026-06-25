"""Concrete SQLAlchemy invoice repository."""

from decimal import Decimal

from sqlalchemy.orm import Session

from src.domain.entities.invoice import Invoice, InvoiceStatus
from src.domain.repositories.invoice_repo import AbstractInvoiceRepository
from src.infrastructure.database.models.invoice import InvoiceModel


def _to_entity(m: InvoiceModel) -> Invoice:
    return Invoice(
        id=m.id,
        idempotency_key=m.idempotency_key,
        amount_usdc=Decimal(str(m.amount_usdc)),
        recipient_address=m.recipient_address,
        payer_address=m.payer_address,
        status=InvoiceStatus(m.status),
        tx_hash=m.tx_hash,
        description=m.description,
        split_rule_id=m.split_rule_id,
        subscription_id=m.subscription_id,
        metadata=m.metadata_ or {},
        created_at=m.created_at,
        paid_at=m.paid_at,
        expires_at=m.expires_at,
    )


class SqlInvoiceRepository(AbstractInvoiceRepository):
    def __init__(self, db: Session) -> None:
        self._db = db

    def save(self, invoice: Invoice) -> Invoice:
        m = InvoiceModel(
            id=invoice.id,
            idempotency_key=invoice.idempotency_key,
            amount_usdc=float(invoice.amount_usdc),
            recipient_address=invoice.recipient_address,
            payer_address=invoice.payer_address,
            status=invoice.status.value,
            tx_hash=invoice.tx_hash,
            description=invoice.description,
            split_rule_id=invoice.split_rule_id,
            subscription_id=invoice.subscription_id,
            metadata_=invoice.metadata,
            paid_at=invoice.paid_at,
            expires_at=invoice.expires_at,
        )
        self._db.add(m)
        self._db.commit()
        self._db.refresh(m)
        return _to_entity(m)

    def find_by_id(self, invoice_id: str) -> Invoice | None:
        m = self._db.get(InvoiceModel, invoice_id)
        return _to_entity(m) if m else None

    def find_by_idempotency_key(self, key: str) -> Invoice | None:
        m = self._db.query(InvoiceModel).filter_by(idempotency_key=key).first()
        return _to_entity(m) if m else None

    def find_by_status(self, status: InvoiceStatus, limit: int = 100) -> list[Invoice]:
        rows = (
            self._db.query(InvoiceModel)
            .filter_by(status=status.value)
            .limit(limit)
            .all()
        )
        return [_to_entity(r) for r in rows]

    def update(self, invoice: Invoice) -> Invoice:
        m = self._db.get(InvoiceModel, invoice.id)
        if not m:
            raise ValueError(f"Invoice {invoice.id} not found")
        m.status = invoice.status.value
        m.tx_hash = invoice.tx_hash
        m.payer_address = invoice.payer_address
        m.paid_at = invoice.paid_at
        m.metadata_ = invoice.metadata
        self._db.commit()
        self._db.refresh(m)
        return _to_entity(m)
