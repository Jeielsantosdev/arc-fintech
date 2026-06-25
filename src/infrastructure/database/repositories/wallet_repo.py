"""Concrete SQLAlchemy wallet repository."""

from sqlalchemy.orm import Session

from src.domain.entities.wallet import Wallet, WalletStatus
from src.domain.repositories.wallet_repo import AbstractWalletRepository
from src.infrastructure.database.models.wallet import WalletModel


def _to_entity(m: WalletModel) -> Wallet:
    return Wallet(
        id=m.id,
        user_id=m.user_id,
        address=m.address,
        encrypted_private_key=m.encrypted_private_key,
        status=WalletStatus(m.status),
        created_at=m.created_at,
    )


def _to_model(w: Wallet) -> WalletModel:
    return WalletModel(
        id=w.id,
        user_id=w.user_id,
        address=w.address,
        encrypted_private_key=w.encrypted_private_key,
        status=w.status.value,
    )


class SqlWalletRepository(AbstractWalletRepository):
    def __init__(self, db: Session) -> None:
        self._db = db

    def save(self, wallet: Wallet) -> Wallet:
        model = _to_model(wallet)
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        return _to_entity(model)

    def find_by_id(self, wallet_id: str) -> Wallet | None:
        m = self._db.get(WalletModel, wallet_id)
        return _to_entity(m) if m else None

    def find_by_user_id(self, user_id: str) -> list[Wallet]:
        rows = self._db.query(WalletModel).filter_by(user_id=user_id).all()
        return [_to_entity(r) for r in rows]

    def find_by_address(self, address: str) -> Wallet | None:
        m = self._db.query(WalletModel).filter_by(address=address).first()
        return _to_entity(m) if m else None
