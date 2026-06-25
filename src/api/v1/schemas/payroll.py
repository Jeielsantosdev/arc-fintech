"""Payroll API schemas."""

from decimal import Decimal

from pydantic import BaseModel, Field


class RegisterEmployeeRequest(BaseModel):
    name: str = Field(..., min_length=1)
    wallet_address: str = Field(..., min_length=42, max_length=42)
    salary_usdc: Decimal = Field(..., gt=0)
    email: str = ""
    department: str = ""
    metadata: dict = Field(default_factory=dict)


class EmployeeResponse(BaseModel):
    employee_id: str
    name: str
    wallet_address: str
    salary_usdc: str
    status: str


class RunPayrollRequest(BaseModel):
    description: str = ""
    employee_ids: list[str] | None = None
    broadcast: bool = True


class PayrollRunResponse(BaseModel):
    run_id: str
    status: str
    total_employees: int
    confirmed: int
    failed: int
    total_amount_usdc: str
    entries: list[dict]
