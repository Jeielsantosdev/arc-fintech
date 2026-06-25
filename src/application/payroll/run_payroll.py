"""
Use case: run international payroll — batch USDC payments to employees.

Arc DevKit: PaymentAgent.execute_batch() processes all salaries in one call
with sequential nonces, minimizing gas overhead.
"""

import logging
from datetime import datetime, timezone
from decimal import Decimal

from src.domain.entities.employee import PayrollEntry, PayrollRun, PayrollRunStatus
from src.domain.repositories.employee_repo import (
    AbstractEmployeeRepository,
    AbstractPayrollRepository,
)
from src.domain.repositories.transaction_repo import AbstractTransactionRepository
from src.domain.entities.transaction import Transaction, TransactionStatus, TransactionType
from src.infrastructure.blockchain.payment_service import PaymentService

logger = logging.getLogger(__name__)


class RunPayrollUseCase:
    """
    Executes international payroll using arc_devkit.PaymentAgent.execute_batch().

    Steps:
      1. Load active employees
      2. Build batch payment list
      3. PaymentAgent.execute_batch() — one nonce sequence
      4. Record each transfer as Transaction
      5. Update PayrollRun with results
    """

    def __init__(
        self,
        emp_repo: AbstractEmployeeRepository,
        payroll_repo: AbstractPayrollRepository,
        tx_repo: AbstractTransactionRepository,
        payment: PaymentService,
    ) -> None:
        self._employees = emp_repo
        self._payroll = payroll_repo
        self._txs = tx_repo
        self._payment = payment

    def execute(
        self,
        description: str = "",
        employee_ids: list[str] | None = None,
        broadcast: bool = True,
    ) -> dict:
        if employee_ids:
            employees = [e for e in [self._employees.find_by_id(eid) for eid in employee_ids] if e]
        else:
            employees = self._employees.find_active()

        if not employees:
            raise ValueError("No active employees found for payroll")

        total = sum(e.salary_usdc for e in employees)
        entries = [
            PayrollEntry(
                employee_id=e.id,
                wallet_address=e.wallet_address,
                amount_usdc=e.salary_usdc,
            )
            for e in employees
        ]

        run = PayrollRun(
            status=PayrollRunStatus.PROCESSING,
            entries=entries,
            total_amount=total,
            description=description,
        )
        run = self._payroll.save(run)

        logger.info(
            "Payroll run %s: %d employees, total %s USDC",
            run.id,
            len(employees),
            total,
        )

        # arc_devkit: PaymentAgent.execute_batch() with sequential nonces
        payments = [
            {"to": e.wallet_address, "amount_usdc": float(e.salary_usdc)}
            for e in employees
        ]
        results = self._payment.send_batch(payments, broadcast=broadcast)

        confirmed = 0
        failed = 0

        for entry, result in zip(run.entries, results):
            status = result.get("status", "failed")
            tx_hash = result.get("tx_hash", "")
            ok = status in ("sent", "confirmed", "signed")

            entry.tx_hash = tx_hash
            entry.status = "confirmed" if ok else "failed"
            if not ok:
                entry.error = str(result)
                failed += 1
            else:
                confirmed += 1

            # Record each salary transfer
            tx = Transaction(
                tx_hash=tx_hash or f"payroll-{run.id}-{entry.employee_id}",
                from_address="platform",
                to_address=entry.wallet_address,
                amount_usdc=entry.amount_usdc,
                tx_type=TransactionType.PAYROLL,
                status=TransactionStatus.CONFIRMED if ok else TransactionStatus.FAILED,
                payroll_run_id=run.id,
                metadata={"employee_id": entry.employee_id, "result": result},
            )
            self._txs.save(tx)

        run.status = (
            PayrollRunStatus.DONE if failed == 0
            else PayrollRunStatus.PARTIAL if confirmed > 0
            else PayrollRunStatus.FAILED
        )
        run.completed_at = datetime.now(timezone.utc)
        self._payroll.update(run)

        return {
            "run_id": run.id,
            "status": run.status.value,
            "total_employees": len(employees),
            "confirmed": confirmed,
            "failed": failed,
            "total_amount_usdc": str(total),
            "description": description,
            "entries": [
                {
                    "employee_id": e.employee_id,
                    "wallet_address": e.wallet_address,
                    "amount_usdc": str(e.amount_usdc),
                    "tx_hash": e.tx_hash,
                    "status": e.status,
                }
                for e in run.entries
            ],
        }
