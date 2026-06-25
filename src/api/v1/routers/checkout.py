"""Checkout endpoint — processes a payment for an invoice."""

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from src.api.dependencies import checkout_uc
from src.api.v1.schemas.invoice import CheckoutRequest, CheckoutResponse
from src.infrastructure.database.session import get_db

router = APIRouter(prefix="/checkout", tags=["checkout"])


@router.post("", response_model=CheckoutResponse)
def process_checkout(
    body: CheckoutRequest,
    background_tasks: BackgroundTasks,
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
):
    """
    Process a USDC payment for an invoice.

    Flow:
      1. Validate invoice
      2. Execute USDC transfer via arc_devkit PaymentAgent
      3. Apply split (if configured)
      4. Renew subscription (if attached)
      5. Fire webhook (if webhook_url provided)

    This is idempotent: supply the same Idempotency-Key to safely retry.
    """
    uc = checkout_uc(db)
    try:
        result = uc.execute(
            invoice_id=body.invoice_id,
            idempotency_key=idempotency_key or body.idempotency_key,
            webhook_url=body.webhook_url,
            broadcast=True,
        )
        return result
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/{invoice_id}")
def get_checkout_status(invoice_id: str, db: Session = Depends(get_db)):
    """Get payment status for a given invoice."""
    from src.infrastructure.database.repositories.invoice_repo import SqlInvoiceRepository
    repo = SqlInvoiceRepository(db)
    invoice = repo.find_by_id(invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return {
        "invoice_id": invoice.id,
        "status": invoice.status.value,
        "tx_hash": invoice.tx_hash,
        "amount_usdc": str(invoice.amount_usdc),
        "paid_at": invoice.paid_at.isoformat() if invoice.paid_at else None,
        "qr_data": f"arc:pay?invoice={invoice.id}&amount={invoice.amount_usdc}&to={invoice.recipient_address}",
    }
