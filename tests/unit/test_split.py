"""Unit tests for split payment use case."""

from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from src.application.split.execute_split import ExecuteSplitUseCase
from src.domain.entities.split import SplitRecipient, SplitRule, SplitStatus


class TestExecuteSplit:
    def _make_uc(self, payment_results):
        tx_repo = MagicMock()
        payment = MagicMock()
        payment.execute_split.return_value = payment_results
        return ExecuteSplitUseCase(tx_repo=tx_repo, payment=payment)

    def test_successful_split(self):
        rule = SplitRule(
            name="platform-merchant",
            recipients=[
                SplitRecipient("0x" + "a" * 40, Decimal("10"), "platform"),
                SplitRecipient("0x" + "b" * 40, Decimal("90"), "merchant"),
            ],
        )
        uc = self._make_uc([
            {"status": "confirmed", "tx_hash": "0x" + "1" * 64},
            {"status": "confirmed", "tx_hash": "0x" + "2" * 64},
        ])
        execution = uc.execute(rule, Decimal("100"), invoice_id="inv-1")
        assert execution.status == SplitStatus.DONE
        assert len(execution.tx_hashes) == 2

    def test_partial_failure_marks_failed(self):
        rule = SplitRule(
            name="partial",
            recipients=[
                SplitRecipient("0x" + "a" * 40, Decimal("50"), "a"),
                SplitRecipient("0x" + "b" * 40, Decimal("50"), "b"),
            ],
        )
        uc = self._make_uc([
            {"status": "confirmed", "tx_hash": "0x" + "1" * 64},
            {"status": "failed", "error": "insufficient funds"},
        ])
        execution = uc.execute(rule, Decimal("100"), invoice_id="inv-2")
        assert execution.status == SplitStatus.FAILED

    def test_build_from_config(self):
        uc = ExecuteSplitUseCase(tx_repo=MagicMock(), payment=MagicMock())
        rule = uc.build_from_config("test", [
            {"address": "0x" + "a" * 40, "percentage": "10", "label": "platform"},
            {"address": "0x" + "b" * 40, "percentage": "90", "label": "merchant"},
        ])
        assert len(rule.recipients) == 2
        rule.validate()  # should not raise
