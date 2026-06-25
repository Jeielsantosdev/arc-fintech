"""Shared pytest fixtures."""

import os
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

# Set required env vars BEFORE any arc_devkit import
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
os.environ.setdefault("ARC_RPC_URL", "http://localhost:8545")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/15")
os.environ.setdefault("KEY_ENCRYPTION_SECRET", "MFun-QOFs1ZFMRUti6UEyM0VUQOloWh1Vgg4cBUKND4=")
os.environ.setdefault("WEBHOOK_SECRET", "test-webhook-secret")


@pytest.fixture
def mock_web3():
    """Mock Web3 to avoid needing a real Arc RPC in unit tests."""
    with patch("arc_devkit.core.connection.get_web3") as mock:
        w3 = MagicMock()
        w3.is_connected.return_value = True
        w3.eth.block_number = 12345
        w3.eth.chain_id = 5042002
        w3.eth.gas_price = 1_000_000_000
        w3.eth.get_balance.return_value = 100 * 10**18
        mock.return_value = w3
        yield w3


@pytest.fixture
def sample_wallet_data():
    return {
        "address": "0xAbCd1234567890AbCd1234567890AbCd12345678",
        "private_key": "0x" + "a" * 64,
    }


@pytest.fixture
def sample_invoice_data():
    return {
        "amount_usdc": Decimal("100.00"),
        "recipient_address": "0xAbCd1234567890AbCd1234567890AbCd12345678",
        "description": "SaaS subscription - Pro Plan",
        "idempotency_key": "test-idem-001",
    }
