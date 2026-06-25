"""Use case: register a new employee for payroll."""

import logging
from decimal import Decimal

from src.domain.entities.employee import Employee
from src.domain.repositories.employee_repo import AbstractEmployeeRepository

logger = logging.getLogger(__name__)


class RegisterEmployeeUseCase:
    def __init__(self, emp_repo: AbstractEmployeeRepository) -> None:
        self._repo = emp_repo

    def execute(
        self,
        name: str,
        wallet_address: str,
        salary_usdc: Decimal,
        email: str = "",
        department: str = "",
        metadata: dict | None = None,
    ) -> dict:
        emp = Employee(
            name=name,
            wallet_address=wallet_address,
            salary_usdc=salary_usdc,
            email=email,
            department=department,
            metadata=metadata or {},
        )
        saved = self._repo.save(emp)
        logger.info("Employee registered: %s (%s)", name, wallet_address)
        return {
            "employee_id": saved.id,
            "name": saved.name,
            "wallet_address": saved.wallet_address,
            "salary_usdc": str(saved.salary_usdc),
            "status": saved.status.value,
        }
