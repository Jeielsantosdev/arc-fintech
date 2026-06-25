"""Use case: create a new invoice / payment request."""

import logging
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from src.domain.entities.invoice import Invoice
from src.domain.repositories.invoice_repo import AbstractInvoiceRepository
from src.infrastructure.cache.redis_client import IdempotencyStore

logger = logging.getLogger(__name__)


class CreateInvoiceUseCase:
    def __init__(
        self,
        invoice_repo: AbstractInvoiceRepository,
        idempotency: IdempotencyStore,
    ) -> None:
        self._repo = invoice_repo
        self._idempotency = idempotency

    def execute(
        self,
        amount_usdc: Decimal,
        recipient_address: str,
        description: str = "",
        idempotency_key: str | None = None,
        split_rule_id: str | None = None,
        subscription_id: str | None = None,
        expires_in_hours: int = 24,
        metadata: dict | None = None,
    ) -> dict:
        idem_key = idempotency_key or str(uuid.uuid4())

        # Return cached result if already processed (replay protection)
        cached = self._idempotency.get(idem_key)
        if cached:
            logger.info("Invoice idempotency hit: %s", idem_key)
            return {**cached, "idempotent": True}

        invoice = Invoice(
            amount_usdc=amount_usdc,
            recipient_address=recipient_address,
            idempotency_key=idem_key,
            description=description,
            split_rule_id=split_rule_id,
            subscription_id=subscription_id,
            metadata=metadata or {},
            expires_at=datetime.now(timezone.utc) + timedelta(hours=expires_in_hours),
        )
        saved = self._repo.save(invoice)

        result = {
            "invoice_id": saved.id,
            "idempotency_key": idem_key,
            "amount_usdc": str(saved.amount_usdc),
            "recipient_address": saved.recipient_address,
            "status": saved.status.value,
            "description": saved.description,
            "expires_at": saved.expires_at.isoformat() if saved.expires_at else None,
            "checkout_url": f"/api/v1/checkout/{saved.id}",
            "qr_data": f"arc:pay?invoice={saved.id}&amount={saved.amount_usdc}&to={saved.recipient_address}",
        }
        self._idempotency.set(idem_key, result)
        logger.info("Invoice created: %s for %s USDC", saved.id, amount_usdc)
        return result
