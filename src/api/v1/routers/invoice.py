"""Invoice endpoints."""

from decimal import Decimal

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from src.api.dependencies import invoice_create_uc
from src.api.v1.schemas.invoice import CreateInvoiceRequest, InvoiceResponse
from src.infrastructure.database.session import get_db

router = APIRouter(prefix="/invoice", tags=["invoice"])


@router.post("", response_model=InvoiceResponse, status_code=201)
def create_invoice(
    body: CreateInvoiceRequest,
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
):
    """
    Create a payment invoice (charge).

    Generates a checkout URL and QR code data for the customer.
    Supply Idempotency-Key header for safe retries.
    """
    uc = invoice_create_uc(db)
    return uc.execute(
        amount_usdc=body.amount_usdc,
        recipient_address=body.recipient_address,
        description=body.description,
        idempotency_key=idempotency_key or body.idempotency_key,
        split_rule_id=body.split_rule_id,
        subscription_id=body.subscription_id,
        expires_in_hours=body.expires_in_hours,
        metadata=body.metadata,
    )


@router.get("/{invoice_id}")
def get_invoice(invoice_id: str, db: Session = Depends(get_db)):
    """Get invoice status by ID."""
    from src.infrastructure.database.repositories.invoice_repo import SqlInvoiceRepository
    repo = SqlInvoiceRepository(db)
    invoice = repo.find_by_id(invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return {
        "invoice_id": invoice.id,
        "status": invoice.status.value,
        "amount_usdc": str(invoice.amount_usdc),
        "recipient_address": invoice.recipient_address,
        "tx_hash": invoice.tx_hash,
        "description": invoice.description,
        "created_at": invoice.created_at.isoformat(),
        "paid_at": invoice.paid_at.isoformat() if invoice.paid_at else None,
    }
