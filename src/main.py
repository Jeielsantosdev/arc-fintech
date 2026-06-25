"""
Arc Fintech Platform — FastAPI application entry point.

Import order matters: src.config must be imported first so that
dotenv is loaded before arc_devkit.config singleton initializes.
"""

import logging

# 1. Load environment BEFORE any arc_devkit import
from src.config import settings  # noqa: F401 — side effect: loads .env

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.v1.routers import (
    checkout,
    health,
    invoice,
    payroll,
    split,
    subscription,
    transactions,
    wallet,
)

logger = structlog.get_logger(__name__)


def create_app() -> FastAPI:
    app = FastAPI(
        title="Arc Fintech Platform",
        description=(
            "Plataforma Fintech para cobrança e movimentação financeira "
            "utilizando USDC na blockchain Arc (Circle)."
        ),
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Global exception handler
    @app.exception_handler(Exception)
    async def global_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.error("Unhandled exception", path=str(request.url), error=str(exc))
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error", "type": type(exc).__name__},
        )

    # Routers
    prefix = settings.api_prefix
    app.include_router(health.router, prefix=prefix)
    app.include_router(wallet.router, prefix=prefix)
    app.include_router(invoice.router, prefix=prefix)
    app.include_router(checkout.router, prefix=prefix)
    app.include_router(subscription.router, prefix=prefix)
    app.include_router(split.router, prefix=prefix)
    app.include_router(payroll.router, prefix=prefix)
    app.include_router(transactions.router, prefix=prefix)

    @app.on_event("startup")
    async def startup() -> None:
        logger.info("Arc Fintech starting", env=settings.app_env)
        _create_tables()

    return app


def _create_tables() -> None:
    """Create all tables if they don't exist (dev/test convenience)."""
    try:
        from src.infrastructure.database.base import Base
        from src.infrastructure.database.models import (  # noqa: F401
            EmployeeModel,
            InvoiceModel,
            PayrollRunModel,
            SplitRuleModel,
            SubscriptionModel,
            TransactionModel,
            WalletModel,
        )
        from src.infrastructure.database.session import engine

        Base.metadata.create_all(bind=engine)
        logger.info("Database tables ensured")
    except Exception as exc:
        logger.warning("Could not create tables (DB may not be ready)", error=str(exc))


app = create_app()
