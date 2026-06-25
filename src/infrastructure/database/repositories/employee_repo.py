"""Concrete SQLAlchemy employee and payroll repositories."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from src.domain.entities.employee import (
    Employee,
    EmployeeStatus,
    PayrollEntry,
    PayrollRun,
    PayrollRunStatus,
)
from src.domain.repositories.employee_repo import (
    AbstractEmployeeRepository,
    AbstractPayrollRepository,
)
from src.infrastructure.database.models.employee import EmployeeModel, PayrollRunModel


def _emp_to_entity(m: EmployeeModel) -> Employee:
    return Employee(
        id=m.id,
        name=m.name,
        wallet_address=m.wallet_address,
        salary_usdc=Decimal(str(m.salary_usdc)),
        email=m.email,
        department=m.department,
        status=EmployeeStatus(m.status),
        metadata=m.metadata_ or {},
        created_at=m.created_at,
    )


def _run_to_entity(m: PayrollRunModel) -> PayrollRun:
    entries_data = m.entries or []
    entries = [
        PayrollEntry(
            employee_id=e["employee_id"],
            wallet_address=e["wallet_address"],
            amount_usdc=Decimal(str(e["amount_usdc"])),
            tx_hash=e.get("tx_hash"),
            status=e.get("status", "pending"),
            error=e.get("error"),
        )
        for e in entries_data
    ]
    return PayrollRun(
        id=m.id,
        status=PayrollRunStatus(m.status),
        entries=entries,
        total_amount=Decimal(str(m.total_amount)),
        description=m.description,
        created_at=m.created_at,
        completed_at=m.completed_at,
        error=m.error,
    )


class SqlEmployeeRepository(AbstractEmployeeRepository):
    def __init__(self, db: Session) -> None:
        self._db = db

    def save(self, emp: Employee) -> Employee:
        m = EmployeeModel(
            id=emp.id,
            name=emp.name,
            wallet_address=emp.wallet_address,
            salary_usdc=float(emp.salary_usdc),
            email=emp.email,
            department=emp.department,
            status=emp.status.value,
            metadata_=emp.metadata,
        )
        self._db.add(m)
        self._db.commit()
        self._db.refresh(m)
        return _emp_to_entity(m)

    def find_by_id(self, emp_id: str) -> Employee | None:
        m = self._db.get(EmployeeModel, emp_id)
        return _emp_to_entity(m) if m else None

    def find_active(self) -> list[Employee]:
        rows = self._db.query(EmployeeModel).filter_by(status="active").all()
        return [_emp_to_entity(r) for r in rows]

    def update(self, emp: Employee) -> Employee:
        m = self._db.get(EmployeeModel, emp.id)
        if not m:
            raise ValueError(f"Employee {emp.id} not found")
        m.name = emp.name
        m.wallet_address = emp.wallet_address
        m.salary_usdc = float(emp.salary_usdc)
        m.status = emp.status.value
        m.metadata_ = emp.metadata
        self._db.commit()
        self._db.refresh(m)
        return _emp_to_entity(m)


class SqlPayrollRepository(AbstractPayrollRepository):
    def __init__(self, db: Session) -> None:
        self._db = db

    def save(self, run: PayrollRun) -> PayrollRun:
        entries_data = [
            {
                "employee_id": e.employee_id,
                "wallet_address": e.wallet_address,
                "amount_usdc": str(e.amount_usdc),
                "tx_hash": e.tx_hash,
                "status": e.status,
                "error": e.error,
            }
            for e in run.entries
        ]
        m = PayrollRunModel(
            id=run.id,
            status=run.status.value,
            total_amount=float(run.total_amount),
            description=run.description,
            entries=entries_data,
            error=run.error,
            completed_at=run.completed_at,
        )
        self._db.add(m)
        self._db.commit()
        self._db.refresh(m)
        return _run_to_entity(m)

    def find_by_id(self, run_id: str) -> PayrollRun | None:
        m = self._db.get(PayrollRunModel, run_id)
        return _run_to_entity(m) if m else None

    def update(self, run: PayrollRun) -> PayrollRun:
        m = self._db.get(PayrollRunModel, run.id)
        if not m:
            raise ValueError(f"PayrollRun {run.id} not found")
        m.status = run.status.value
        m.total_amount = float(run.total_amount)
        m.entries = [
            {
                "employee_id": e.employee_id,
                "wallet_address": e.wallet_address,
                "amount_usdc": str(e.amount_usdc),
                "tx_hash": e.tx_hash,
                "status": e.status,
                "error": e.error,
            }
            for e in run.entries
        ]
        m.completed_at = run.completed_at
        m.error = run.error
        self._db.commit()
        self._db.refresh(m)
        return _run_to_entity(m)
