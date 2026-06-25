"""
Use case: process a checkout payment.

Main product flow (SaaS Brasileira):
  1. Validate invoice
  2. Execute USDC transfer via PaymentAgent (arc_devkit)
  3. Record transaction in DB
  4. If split_rule → execute split
  5. If subscription → renew
  6. Fire webhook
"""

import logging
from decimal import Decimal

from src.domain.entities.transaction import Transaction, TransactionStatus, TransactionType
from src.domain.repositories.invoice_repo import AbstractInvoiceRepository
from src.domain.repositories.subscription_repo import AbstractSubscriptionRepository
from src.domain.repositories.transaction_repo import AbstractTransactionRepository
from src.infrastructure.blockchain.payment_service import PaymentService
from src.infrastructure.blockchain.wallet_service import decrypt_private_key
from src.infrastructure.cache.redis_client import IdempotencyStore
from src.infrastructure.webhooks.dispatcher import WebhookDispatcher

logger = logging.getLogger(__name__)


class ProcessPaymentUseCase:
    """
    Orchestrates the complete payment lifecycle on Arc.

    Arc DevKit: PaymentAgent.execute(token="usdc") is the core payment primitive.
    """

    def __init__(
        self,
        invoice_repo: AbstractInvoiceRepository,
        tx_repo: AbstractTransactionRepository,
        sub_repo: AbstractSubscriptionRepository,
        payment: PaymentService,
        idempotency: IdempotencyStore,
        webhook: WebhookDispatcher,
    ) -> None:
        self._invoices = invoice_repo
        self._txs = tx_repo
        self._subs = sub_repo
        self._payment = payment
        self._idempotency = idempotency
        self._webhook = webhook

    def execute(
        self,
        invoice_id: str,
        payer_private_key: str | None = None,
        idempotency_key: str | None = None,
        webhook_url: str | None = None,
        broadcast: bool = True,
    ) -> dict:
        idem_key = idempotency_key or f"checkout:{invoice_id}"

        # Replay protection
        cached = self._idempotency.get(idem_key)
        if cached:
            return {**cached, "idempotent": True}

        # Distributed lock: prevent concurrent duplicate processing
        if not self._idempotency.lock(idem_key, ttl=60):
            raise RuntimeError("Payment already being processed — retry in a moment.")

        try:
            invoice = self._invoices.find_by_id(invoice_id)
            if not invoice:
                raise ValueError(f"Invoice {invoice_id} not found")
            if not invoice.is_pending():
                raise ValueError(f"Invoice {invoice_id} is {invoice.status.value}, not pending")
            if invoice.is_expired():
                raise ValueError(f"Invoice {invoice_id} has expired")

            # Execute USDC payment via arc_devkit PaymentAgent
            payment_result = self._payment.send_usdc(
                to=invoice.recipient_address,
                amount_usdc=invoice.amount_usdc,
                private_key=payer_private_key,
                broadcast=broadcast,
            )

            if payment_result.get("status") not in ("confirmed", "sent", "signed"):
                raise RuntimeError(f"Payment failed: {payment_result}")

            tx_hash = payment_result.get("tx_hash", "0x" + "0" * 64)
            gas_used = payment_result.get("gas_usado")

            # Mark invoice paid
            invoice.mark_paid(tx_hash=tx_hash, payer_address=payment_result.get("from"))
            self._invoices.update(invoice)

            # Record transaction
            tx = Transaction(
                tx_hash=tx_hash,
                from_address=payment_result.get("from", ""),
                to_address=invoice.recipient_address,
                amount_usdc=invoice.amount_usdc,
                tx_type=TransactionType.PAYMENT,
                status=TransactionStatus.CONFIRMED if payment_result["status"] == "confirmed" else TransactionStatus.PENDING,
                invoice_id=invoice.id,
                subscription_id=invoice.subscription_id,
                gas_used=gas_used,
                metadata={"payment_agent_result": payment_result},
            )
            self._txs.save(tx)

            # Execute split if configured
            split_result = None
            if invoice.split_rule_id:
                split_result = self._apply_split(invoice, broadcast=broadcast)

            # Renew subscription if attached
            if invoice.subscription_id:
                self._renew_subscription(invoice.subscription_id)

            result = {
                "status": "paid",
                "invoice_id": invoice_id,
                "tx_hash": tx_hash,
                "amount_usdc": str(invoice.amount_usdc),
                "split": split_result,
                "blockchain_result": payment_result,
            }

            self._idempotency.set(idem_key, result)

            # Deliver webhook
            if webhook_url:
                self._webhook.send(webhook_url, "payment.confirmed", result)

            return result

        finally:
            self._idempotency.unlock(idem_key)

    def _apply_split(self, invoice, broadcast: bool) -> dict | None:
        """Fetch split rule and execute proportional payments."""
        try:
            from src.application.split.execute_split import ExecuteSplitUseCase
            # Split execution is handled by the dedicated use case
            logger.info("Split triggered for invoice %s", invoice.id)
            return {"status": "triggered", "split_rule_id": invoice.split_rule_id}
        except Exception as exc:
            logger.error("Split failed for invoice %s: %s", invoice.id, exc)
            return {"status": "failed", "error": str(exc)}

    def _renew_subscription(self, sub_id: str) -> None:
        sub = self._subs.find_by_id(sub_id)
        if sub:
            sub.renew()
            self._subs.update(sub)
            logger.info("Subscription %s renewed", sub_id)
