"""Unit tests for domain entities — no external dependencies."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from src.domain.entities.invoice import Invoice, InvoiceStatus
from src.domain.entities.split import SplitRecipient, SplitRule
from src.domain.entities.subscription import Subscription, SubscriptionStatus
from src.domain.entities.transaction import Transaction, TransactionStatus, TransactionType


class TestInvoice:
    def test_mark_paid(self):
        inv = Invoice(
            amount_usdc=Decimal("100"),
            recipient_address="0x" + "a" * 40,
            idempotency_key="key-1",
        )
        inv.mark_paid(tx_hash="0x" + "b" * 64, payer_address="0x" + "c" * 40)
        assert inv.status == InvoiceStatus.PAID
        assert inv.tx_hash == "0x" + "b" * 64
        assert inv.paid_at is not None

    def test_is_expired_by_status(self):
        inv = Invoice(
            amount_usdc=Decimal("50"),
            recipient_address="0x" + "a" * 40,
            idempotency_key="key-2",
        )
        inv.status = InvoiceStatus.EXPIRED
        assert inv.is_expired()

    def test_is_expired_by_time(self):
        inv = Invoice(
            amount_usdc=Decimal("50"),
            recipient_address="0x" + "a" * 40,
            idempotency_key="key-3",
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        assert inv.is_expired()

    def test_is_pending(self):
        inv = Invoice(
            amount_usdc=Decimal("10"),
            recipient_address="0x" + "a" * 40,
            idempotency_key="key-4",
        )
        assert inv.is_pending()


class TestSubscription:
    def _make_sub(self) -> Subscription:
        return Subscription(
            customer_address="0x" + "c" * 40,
            merchant_address="0x" + "m" * 40,
            amount_usdc=Decimal("99.99"),
            interval_days=30,
        )

    def test_renew_advances_due_date(self):
        sub = self._make_sub()
        sub.renew()
        assert sub.status == SubscriptionStatus.ACTIVE
        assert sub.next_due_at > datetime.now(timezone.utc)
        assert sub.retry_count == 0

    def test_record_failure_suspends_after_max_retries(self):
        sub = self._make_sub()
        sub.max_retries = 3
        sub.record_failure()
        sub.record_failure()
        sub.record_failure()
        assert sub.status == SubscriptionStatus.SUSPENDED

    def test_cancel(self):
        sub = self._make_sub()
        sub.cancel()
        assert sub.status == SubscriptionStatus.CANCELLED
        assert sub.cancelled_at is not None

    def test_is_due(self):
        sub = self._make_sub()
        sub.next_due_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        assert sub.is_due()


class TestSplitRule:
    def test_validates_sum_to_100(self):
        rule = SplitRule(
            name="test",
            recipients=[
                SplitRecipient("0x" + "a" * 40, Decimal("10"), "platform"),
                SplitRecipient("0x" + "b" * 40, Decimal("90"), "merchant"),
            ],
        )
        rule.validate()  # should not raise

    def test_raises_when_not_100(self):
        rule = SplitRule(
            name="bad",
            recipients=[
                SplitRecipient("0x" + "a" * 40, Decimal("50"), "a"),
                SplitRecipient("0x" + "b" * 40, Decimal("40"), "b"),
            ],
        )
        with pytest.raises(ValueError, match="100"):
            rule.validate()

    def test_amount_for(self):
        r = SplitRecipient("0x" + "a" * 40, Decimal("10"), "platform")
        amount = r.amount_for(Decimal("100"))
        assert amount == Decimal("10.000000")

    def test_breakdown(self):
        rule = SplitRule(
            name="saas-split",
            recipients=[
                SplitRecipient("0x" + "a" * 40, Decimal("10"), "platform"),
                SplitRecipient("0x" + "b" * 40, Decimal("90"), "merchant"),
            ],
        )
        bd = rule.breakdown(Decimal("100"))
        assert len(bd) == 2
        assert bd[0]["amount_usdc"] == "10.000000"
        assert bd[1]["amount_usdc"] == "90.000000"


class TestTransaction:
    def test_confirm(self):
        tx = Transaction(
            tx_hash="0x" + "a" * 64,
            from_address="0x" + "f" * 40,
            to_address="0x" + "t" * 40,
            amount_usdc=Decimal("50"),
            tx_type=TransactionType.PAYMENT,
        )
        tx.confirm(gas_used=21000)
        assert tx.status == TransactionStatus.CONFIRMED
        assert tx.gas_used == 21000
        assert tx.confirmed_at is not None
