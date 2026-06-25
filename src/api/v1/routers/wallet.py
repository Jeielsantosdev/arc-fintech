"""Wallet endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.api.dependencies import wallet_balance_uc, wallet_create_uc, wallet_history_uc
from src.api.v1.schemas.wallet import BalanceResponse, CreateWalletRequest, WalletResponse
from src.infrastructure.database.session import get_db

router = APIRouter(prefix="/wallet", tags=["wallet"])


@router.post("/create", response_model=WalletResponse, status_code=201)
def create_wallet(body: CreateWalletRequest, db: Session = Depends(get_db)):
    """
    Create a new Arc wallet for a user.

    Uses arc_devkit.core.wallet.create_wallet() to generate the keypair.
    Private key is Fernet-encrypted before storage.
    """
    uc = wallet_create_uc(db)
    return uc.execute(user_id=body.user_id)


@router.get("/{address}/balance", response_model=BalanceResponse)
def get_balance(address: str, db: Session = Depends(get_db)):
    """
    Get native ARC + USDC balance for an address.

    Uses arc_devkit.core.wallet.get_balance() and USDCToken.balance().
    """
    uc = wallet_balance_uc(db)
    try:
        return uc.execute(address=address)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{address}/transactions")
def get_transactions(
    address: str,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """
    Get transaction history for an address.

    Combines DB-recorded transactions with arc_devkit PortfolioAnalyzer on-chain scan.
    """
    uc = wallet_history_uc(db)
    return uc.execute(address=address, limit=limit, offset=offset)
