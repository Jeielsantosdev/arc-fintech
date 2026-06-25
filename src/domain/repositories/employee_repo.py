"""Abstract employee and payroll repository."""

from abc import ABC, abstractmethod

from src.domain.entities.employee import Employee, PayrollRun


class AbstractEmployeeRepository(ABC):
    @abstractmethod
    def save(self, employee: Employee) -> Employee: ...

    @abstractmethod
    def find_by_id(self, emp_id: str) -> Employee | None: ...

    @abstractmethod
    def find_active(self) -> list[Employee]: ...

    @abstractmethod
    def update(self, employee: Employee) -> Employee: ...


class AbstractPayrollRepository(ABC):
    @abstractmethod
    def save(self, run: PayrollRun) -> PayrollRun: ...

    @abstractmethod
    def find_by_id(self, run_id: str) -> PayrollRun | None: ...

    @abstractmethod
    def update(self, run: PayrollRun) -> PayrollRun: ...
