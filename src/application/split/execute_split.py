"""
Use case: execute a split payment.

Example: Invoice of 100 USDC
  Platform (10%)  → 10 USDC
  Merchant (90%)  → 90 USDC
"""

import logging
from decimal import Decimal

from src.domain.entities.split import SplitExecution, SplitRecipient, SplitRule, SplitStatus
from src.domain.entities.transaction import Transaction, TransactionStatus, TransactionType
from src.domain.repositories.transaction_repo import AbstractTransactionRepository
from src.infrastructure.blockchain.payment_service import PaymentService

logger = logging.getLogger(__name__)


class ExecuteSplitUseCase:
    """
    Divides a payment among multiple recipients via PaymentAgent.execute_batch().

    Arc DevKit: PaymentService.execute_split() → PaymentAgent.execute_batch()
    """

    def __init__(
        self,
        tx_repo: AbstractTransactionRepository,
        payment: PaymentService,
    ) -> None:
        self._txs = tx_repo
        self._payment = payment

    def execute(
        self,
        split_rule: SplitRule,
        total_amount: Decimal,
        invoice_id: str | None = None,
        broadcast: bool = True,
    ) -> SplitExecution:
        split_rule.validate()

        execution = SplitExecution(
            split_rule_id=split_rule.id,
            invoice_id=invoice_id or "",
            total_amount=total_amount,
        )
        execution.status = SplitStatus.EXECUTING

        recipients = [
            {
                "to": r.address,
                "amount_usdc": r.amount_for(total_amount),
                "label": r.label,
            }
            for r in split_rule.recipients
        ]

        logger.info(
            "Executing split: %s | total=%s USDC | %d recipients",
            split_rule.name,
            total_amount,
            len(recipients),
        )

        # arc_devkit: PaymentAgent.execute_batch() with incremental nonces
        results = self._payment.execute_split(recipients, broadcast=broadcast)

        tx_hashes = []
        all_ok = True

        for idx, (recipient, result) in enumerate(zip(recipients, results)):
            tx_hash = result.get("tx_hash", "")
            status_val = result.get("status", "failed")
            ok = status_val in ("sent", "confirmed", "signed")

            if not ok:
                all_ok = False
                logger.warning(
                    "Split recipient %s failed: %s", recipient["to"], result
                )

            if tx_hash:
                tx_hashes.append(tx_hash)

            # Record each split transfer as a transaction
            tx = Transaction(
                tx_hash=tx_hash or f"split-{execution.id}-{idx}",
                from_address="platform",
                to_address=recipient["to"],
                amount_usdc=recipient["amount_usdc"],
                tx_type=TransactionType.SPLIT,
                status=TransactionStatus.CONFIRMED if ok else TransactionStatus.FAILED,
                invoice_id=invoice_id,
                metadata={
                    "split_rule_id": split_rule.id,
                    "label": recipient.get("label", ""),
                    "blockchain_result": result,
                },
            )
            self._txs.save(tx)

        execution.tx_hashes = tx_hashes
        execution.status = SplitStatus.DONE if all_ok else SplitStatus.FAILED

        return execution

    def build_from_config(
        self,
        name: str,
        recipients_config: list[dict],
    ) -> SplitRule:
        """
        Build a SplitRule from a list of {address, percentage, label} dicts.

        Example:
          [{"address": "0xPlatform", "percentage": "10", "label": "platform"},
           {"address": "0xMerchant", "percentage": "90", "label": "merchant"}]
        """
        recipients = [
            SplitRecipient(
                address=r["address"],
                percentage=Decimal(str(r["percentage"])),
                label=r.get("label", ""),
            )
            for r in recipients_config
        ]
        rule = SplitRule(name=name, recipients=recipients)
        rule.validate()
        return rule
