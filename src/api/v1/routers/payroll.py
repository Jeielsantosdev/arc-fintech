"""Payroll endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.api.dependencies import employee_register_uc, payroll_run_uc
from src.api.v1.schemas.payroll import (
    EmployeeResponse,
    PayrollRunResponse,
    RegisterEmployeeRequest,
    RunPayrollRequest,
)
from src.infrastructure.database.session import get_db

router = APIRouter(prefix="/payroll", tags=["payroll"])


@router.post("/employee", response_model=EmployeeResponse, status_code=201)
def register_employee(body: RegisterEmployeeRequest, db: Session = Depends(get_db)):
    """Register a new employee for international payroll."""
    uc = employee_register_uc(db)
    return uc.execute(
        name=body.name,
        wallet_address=body.wallet_address,
        salary_usdc=body.salary_usdc,
        email=body.email,
        department=body.department,
        metadata=body.metadata,
    )


@router.post("/run", response_model=PayrollRunResponse)
def run_payroll(body: RunPayrollRequest, db: Session = Depends(get_db)):
    """
    Execute international payroll — batch USDC payments to all active employees.

    Uses arc_devkit PaymentAgent.execute_batch() with sequential nonces.
    Returns a full execution report per employee.
    """
    uc = payroll_run_uc(db)
    try:
        return uc.execute(
            description=body.description,
            employee_ids=body.employee_ids,
            broadcast=body.broadcast,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
