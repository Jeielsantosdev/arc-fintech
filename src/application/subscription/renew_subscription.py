"""Use case: process due subscriptions (called by background worker)."""

import logging
from datetime import datetime, timezone

from src.domain.repositories.invoice_repo import AbstractInvoiceRepository
from src.domain.repositories.subscription_repo import AbstractSubscriptionRepository
from src.domain.repositories.transaction_repo import AbstractTransactionRepository
from src.infrastructure.blockchain.payment_service import PaymentService
from src.infrastructure.cache.redis_client import IdempotencyStore
from src.infrastructure.webhooks.dispatcher import WebhookDispatcher

logger = logging.getLogger(__name__)


class RenewSubscriptionUseCase:
    """
    Processes all due subscriptions with retry logic.

    For each due subscription:
      1. Attempt USDC payment via PaymentAgent (arc_devkit)
      2. On success → sub.renew() (advance next_due_at by interval_days)
      3. On failure → sub.record_failure() → suspend after max_retries
    """

    def __init__(
        self,
        sub_repo: AbstractSubscriptionRepository,
        invoice_repo: AbstractInvoiceRepository,
        tx_repo: AbstractTransactionRepository,
        payment: PaymentService,
        idempotency: IdempotencyStore,
        webhook: WebhookDispatcher,
    ) -> None:
        self._subs = sub_repo
        self._invoices = invoice_repo
        self._txs = tx_repo
        self._payment = payment
        self._idempotency = idempotency
        self._webhook = webhook

    def process_due(self, webhook_url: str | None = None) -> dict:
        now = datetime.now(timezone.utc)
        due = self._subs.find_due(before=now)
        logger.info("Processing %d due subscriptions", len(due))

        results = {"processed": 0, "renewed": 0, "failed": 0, "suspended": 0}

        for sub in due:
            idem_key = f"sub-renewal:{sub.id}:{now.date()}"
            if self._idempotency.exists(idem_key):
                logger.debug("Subscription %s already processed today", sub.id)
                continue

            try:
                result = self._payment.send_usdc(
                    to=sub.merchant_address,
                    amount_usdc=sub.amount_usdc,
                    broadcast=True,
                )

                if result.get("status") in ("confirmed", "sent"):
                    sub.renew()
                    self._subs.update(sub)
                    results["renewed"] += 1
                    self._idempotency.set(idem_key, {"status": "renewed"})
                    logger.info("Subscription %s renewed", sub.id)

                    if webhook_url:
                        self._webhook.send(webhook_url, "subscription.renewed", {
                            "subscription_id": sub.id,
                            "amount_usdc": str(sub.amount_usdc),
                            "tx_hash": result.get("tx_hash"),
                            "next_due_at": sub.next_due_at.isoformat(),
                        })
                else:
                    raise RuntimeError(f"Payment returned status: {result.get('status')}")

            except Exception as exc:
                logger.warning("Subscription %s renewal failed: %s", sub.id, exc)
                sub.record_failure()
                self._subs.update(sub)
                results["failed"] += 1
                if sub.status.value == "suspended":
                    results["suspended"] += 1
                    if webhook_url:
                        self._webhook.send(webhook_url, "subscription.suspended", {
                            "subscription_id": sub.id,
                            "reason": str(exc),
                        })

            results["processed"] += 1

        return results
