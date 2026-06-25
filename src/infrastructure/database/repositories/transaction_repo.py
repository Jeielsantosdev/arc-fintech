"""Concrete SQLAlchemy transaction repository."""

from decimal import Decimal

from sqlalchemy.orm import Session

from src.domain.entities.transaction import Transaction, TransactionStatus, TransactionType
from src.domain.repositories.transaction_repo import AbstractTransactionRepository
from src.infrastructure.database.models.transaction import TransactionModel


def _to_entity(m: TransactionModel) -> Transaction:
    return Transaction(
        id=m.id,
        tx_hash=m.tx_hash,
        from_address=m.from_address,
        to_address=m.to_address,
        amount_usdc=Decimal(str(m.amount_usdc)),
        tx_type=TransactionType(m.tx_type),
        status=TransactionStatus(m.status),
        invoice_id=m.invoice_id,
        subscription_id=m.subscription_id,
        payroll_run_id=m.payroll_run_id,
        gas_used=m.gas_used,
        metadata=m.metadata_ or {},
        created_at=m.created_at,
        confirmed_at=m.confirmed_at,
    )


class SqlTransactionRepository(AbstractTransactionRepository):
    def __init__(self, db: Session) -> None:
        self._db = db

    def save(self, tx: Transaction) -> Transaction:
        m = TransactionModel(
            id=tx.id,
            tx_hash=tx.tx_hash,
            from_address=tx.from_address,
            to_address=tx.to_address,
            amount_usdc=float(tx.amount_usdc),
            tx_type=tx.tx_type.value,
            status=tx.status.value,
            invoice_id=tx.invoice_id,
            subscription_id=tx.subscription_id,
            payroll_run_id=tx.payroll_run_id,
            gas_used=tx.gas_used,
            metadata_=tx.metadata,
            confirmed_at=tx.confirmed_at,
        )
        self._db.add(m)
        self._db.commit()
        self._db.refresh(m)
        return _to_entity(m)

    def find_by_id(self, tx_id: str) -> Transaction | None:
        m = self._db.get(TransactionModel, tx_id)
        return _to_entity(m) if m else None

    def find_by_tx_hash(self, tx_hash: str) -> Transaction | None:
        m = self._db.query(TransactionModel).filter_by(tx_hash=tx_hash).first()
        return _to_entity(m) if m else None

    def find_by_address(self, address: str, limit: int = 50, offset: int = 0) -> list[Transaction]:
        rows = (
            self._db.query(TransactionModel)
            .filter(
                (TransactionModel.from_address == address)
                | (TransactionModel.to_address == address)
            )
            .order_by(TransactionModel.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        return [_to_entity(r) for r in rows]

    def update(self, tx: Transaction) -> Transaction:
        m = self._db.get(TransactionModel, tx.id)
        if not m:
            raise ValueError(f"Transaction {tx.id} not found")
        m.status = tx.status.value
        m.gas_used = tx.gas_used
        m.confirmed_at = tx.confirmed_at
        m.metadata_ = tx.metadata
        self._db.commit()
        self._db.refresh(m)
        return _to_entity(m)
