"""Transaction history endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.api.dependencies import wallet_history_uc
from src.infrastructure.database.session import get_db

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.get("")
def list_transactions(
    address: str,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """
    Get transaction history for an address.

    Combines DB-indexed records with arc_devkit PortfolioAnalyzer on-chain scan.
    """
    uc = wallet_history_uc(db)
    return uc.execute(address=address, limit=limit, offset=offset)


@router.get("/{tx_hash}")
def get_transaction(tx_hash: str, db: Session = Depends(get_db)):
    """Lookup a single transaction by its on-chain hash."""
    from src.infrastructure.database.repositories.transaction_repo import SqlTransactionRepository
    repo = SqlTransactionRepository(db)
    tx = repo.find_by_tx_hash(tx_hash)
    if not tx:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Transaction not found")
    return {
        "id": tx.id,
        "tx_hash": tx.tx_hash,
        "from": tx.from_address,
        "to": tx.to_address,
        "amount_usdc": str(tx.amount_usdc),
        "type": tx.tx_type.value,
        "status": tx.status.value,
        "created_at": tx.created_at.isoformat(),
        "confirmed_at": tx.confirmed_at.isoformat() if tx.confirmed_at else None,
    }
