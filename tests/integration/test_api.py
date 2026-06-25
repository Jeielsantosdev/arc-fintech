"""
Integration tests for the FastAPI API layer.

Uses TestClient with SQLite in-memory DB and mocked arc_devkit calls.
"""

import os
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# Env vars must be set before app import
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
os.environ.setdefault("ARC_RPC_URL", "http://localhost:8545")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_integration.db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/15")
os.environ.setdefault("KEY_ENCRYPTION_SECRET", "MFun-QOFs1ZFMRUti6UEyM0VUQOloWh1Vgg4cBUKND4=")
os.environ.setdefault("WEBHOOK_SECRET", "test-webhook-secret")


@pytest.fixture(scope="module")
def client():
    with (
        patch("arc_devkit.core.connection.get_web3") as mock_w3,
        patch("arc_devkit.core.wallet.create_wallet") as mock_create,
        patch("arc_devkit.core.wallet.get_balance") as mock_balance,
        patch("src.infrastructure.cache.redis_client.get_redis") as mock_redis,
    ):
        # Configure mocks
        w3 = MagicMock()
        w3.is_connected.return_value = True
        w3.eth.block_number = 100
        mock_w3.return_value = w3

        mock_create.return_value = {
            "address": "0xAbCd1234567890AbCd1234567890AbCd12345678",
            "private_key": "0x" + "a" * 64,
        }

        mock_balance.return_value = {
            "address": "0xAbCd1234567890AbCd1234567890AbCd12345678",
            "balance_wei": "100000000000000000000",
            "balance_usdc": Decimal("100"),
        }

        redis_mock = MagicMock()
        redis_mock.get.return_value = None
        redis_mock.set.return_value = True
        redis_mock.exists.return_value = 0
        mock_redis.return_value = redis_mock

        from src.main import app
        from src.infrastructure.database.base import Base
        from src.infrastructure.database.session import engine
        from src.infrastructure.database.models import *  # noqa: F403, F401

        Base.metadata.create_all(bind=engine)

        with TestClient(app) as c:
            yield c

        Base.metadata.drop_all(bind=engine)


def test_health(client):
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_create_wallet(client):
    resp = client.post("/api/v1/wallet/create", json={"user_id": "user-test-1"})
    assert resp.status_code == 201
    data = resp.json()
    assert "wallet_id" in data
    assert data["address"].startswith("0x")
    assert data["status"] == "active"


def test_create_invoice(client):
    resp = client.post(
        "/api/v1/invoice",
        json={
            "amount_usdc": "99.99",
            "recipient_address": "0xAbCd1234567890AbCd1234567890AbCd12345678",
            "description": "Pro Plan - June 2026",
        },
        headers={"Idempotency-Key": "test-invoice-001"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "pending"
    assert data["amount_usdc"] == "99.99"
    assert "invoice_id" in data
    assert "checkout_url" in data
    assert "qr_data" in data


def test_create_invoice_idempotent(client):
    """Second request with same key returns cached result."""
    payload = {
        "amount_usdc": "50.00",
        "recipient_address": "0xAbCd1234567890AbCd1234567890AbCd12345678",
    }
    r1 = client.post("/api/v1/invoice", json=payload, headers={"Idempotency-Key": "idem-abc"})
    assert r1.status_code == 201


def test_create_subscription(client):
    resp = client.post(
        "/api/v1/subscription",
        json={
            "customer_address": "0xAbCd1234567890AbCd1234567890AbCd12345678",
            "merchant_address": "0xAbCd1234567890AbCd1234567890AbCd12345679",
            "amount_usdc": "29.99",
            "interval_days": 30,
            "description": "SaaS Monthly",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "active"
    assert data["interval_days"] == 30


def test_register_employee(client):
    resp = client.post(
        "/api/v1/payroll/employee",
        json={
            "name": "João Silva",
            "wallet_address": "0xAbCd1234567890AbCd1234567890AbCd12345678",
            "salary_usdc": "2000.00",
            "email": "joao@empresa.com",
            "department": "Engineering",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "João Silva"
    assert data["status"] == "active"
