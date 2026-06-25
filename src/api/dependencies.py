"""FastAPI dependency injection — wires use cases with real implementations."""

from functools import lru_cache

from sqlalchemy.orm import Session

from src.application.checkout.create_invoice import CreateInvoiceUseCase
from src.application.checkout.process_payment import ProcessPaymentUseCase
from src.application.payroll.register_employee import RegisterEmployeeUseCase
from src.application.payroll.run_payroll import RunPayrollUseCase
from src.application.split.execute_split import ExecuteSplitUseCase
from src.application.subscription.cancel_subscription import CancelSubscriptionUseCase
from src.application.subscription.create_subscription import CreateSubscriptionUseCase
from src.application.subscription.renew_subscription import RenewSubscriptionUseCase
from src.application.wallet.create_wallet import CreateWalletUseCase
from src.application.wallet.get_balance import GetBalanceUseCase
from src.application.wallet.get_history import GetTransactionHistoryUseCase
from src.infrastructure.blockchain.monitor_service import MonitorService
from src.infrastructure.blockchain.payment_service import PaymentService
from src.infrastructure.blockchain.wallet_service import WalletService
from src.infrastructure.cache.redis_client import IdempotencyStore, get_redis
from src.infrastructure.database.repositories.employee_repo import (
    SqlEmployeeRepository,
    SqlPayrollRepository,
)
from src.infrastructure.database.repositories.invoice_repo import SqlInvoiceRepository
from src.infrastructure.database.repositories.subscription_repo import SqlSubscriptionRepository
from src.infrastructure.database.repositories.transaction_repo import SqlTransactionRepository
from src.infrastructure.database.repositories.wallet_repo import SqlWalletRepository
from src.infrastructure.database.session import get_db
from src.infrastructure.webhooks.dispatcher import WebhookDispatcher


# ── Singleton services ────────────────────────────────────────────────────────

@lru_cache
def get_wallet_service() -> WalletService:
    return WalletService()


@lru_cache
def get_payment_service() -> PaymentService:
    return PaymentService()


@lru_cache
def get_monitor_service() -> MonitorService:
    return MonitorService()


@lru_cache
def get_webhook_dispatcher() -> WebhookDispatcher:
    return WebhookDispatcher()


def get_idempotency() -> IdempotencyStore:
    return IdempotencyStore(get_redis())


# ── Use case factories ────────────────────────────────────────────────────────

def wallet_create_uc(db: Session) -> CreateWalletUseCase:
    return CreateWalletUseCase(SqlWalletRepository(db), get_wallet_service())


def wallet_balance_uc(db: Session) -> GetBalanceUseCase:
    return GetBalanceUseCase(SqlWalletRepository(db), get_wallet_service())


def wallet_history_uc(db: Session) -> GetTransactionHistoryUseCase:
    return GetTransactionHistoryUseCase(SqlTransactionRepository(db), get_wallet_service())


def invoice_create_uc(db: Session) -> CreateInvoiceUseCase:
    return CreateInvoiceUseCase(SqlInvoiceRepository(db), get_idempotency())


def checkout_uc(db: Session) -> ProcessPaymentUseCase:
    return ProcessPaymentUseCase(
        invoice_repo=SqlInvoiceRepository(db),
        tx_repo=SqlTransactionRepository(db),
        sub_repo=SqlSubscriptionRepository(db),
        payment=get_payment_service(),
        idempotency=get_idempotency(),
        webhook=get_webhook_dispatcher(),
    )


def split_uc(db: Session) -> ExecuteSplitUseCase:
    return ExecuteSplitUseCase(SqlTransactionRepository(db), get_payment_service())


def subscription_create_uc(db: Session) -> CreateSubscriptionUseCase:
    return CreateSubscriptionUseCase(SqlSubscriptionRepository(db))


def subscription_cancel_uc(db: Session) -> CancelSubscriptionUseCase:
    return CancelSubscriptionUseCase(SqlSubscriptionRepository(db))


def subscription_renew_uc(db: Session) -> RenewSubscriptionUseCase:
    return RenewSubscriptionUseCase(
        sub_repo=SqlSubscriptionRepository(db),
        invoice_repo=SqlInvoiceRepository(db),
        tx_repo=SqlTransactionRepository(db),
        payment=get_payment_service(),
        idempotency=get_idempotency(),
        webhook=get_webhook_dispatcher(),
    )


def employee_register_uc(db: Session) -> RegisterEmployeeUseCase:
    return RegisterEmployeeUseCase(SqlEmployeeRepository(db))


def payroll_run_uc(db: Session) -> RunPayrollUseCase:
    return RunPayrollUseCase(
        emp_repo=SqlEmployeeRepository(db),
        payroll_repo=SqlPayrollRepository(db),
        tx_repo=SqlTransactionRepository(db),
        payment=get_payment_service(),
    )
