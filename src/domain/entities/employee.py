"""Employee domain entity — for international payroll."""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum


class EmployeeStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class PayrollRunStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    DONE = "done"
    PARTIAL = "partial"
    FAILED = "failed"


@dataclass
class Employee:
    name: str
    wallet_address: str
    salary_usdc: Decimal
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    email: str = ""
    department: str = ""
    status: EmployeeStatus = EmployeeStatus.ACTIVE
    metadata: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def is_active(self) -> bool:
        return self.status == EmployeeStatus.ACTIVE


@dataclass
class PayrollEntry:
    employee_id: str
    wallet_address: str
    amount_usdc: Decimal
    tx_hash: str | None = None
    status: str = "pending"
    error: str | None = None


@dataclass
class PayrollRun:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: PayrollRunStatus = PayrollRunStatus.PENDING
    entries: list[PayrollEntry] = field(default_factory=list)
    total_amount: Decimal = Decimal("0")
    description: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None
    error: str | None = None

    def summary(self) -> dict:
        paid = [e for e in self.entries if e.status == "confirmed"]
        failed = [e for e in self.entries if e.status == "failed"]
        return {
            "run_id": self.id,
            "status": self.status,
            "total_employees": len(self.entries),
            "paid": len(paid),
            "failed": len(failed),
            "total_amount_usdc": str(self.total_amount),
        }
