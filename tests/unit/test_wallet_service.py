"""Unit tests for wallet service — mocks arc_devkit calls."""

from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from src.infrastructure.blockchain.wallet_service import (
    WalletService,
    decrypt_private_key,
    encrypt_private_key,
)


class TestKeyEncryption:
    def test_encrypt_decrypt_roundtrip(self):
        key = "0x" + "a" * 64
        encrypted = encrypt_private_key(key)
        assert encrypted != key
        assert decrypt_private_key(encrypted) == key


class TestWalletService:
    @patch("arc_devkit.core.wallet.create_wallet")
    def test_create_wallet_calls_arc_devkit(self, mock_create):
        mock_create.return_value = {
            "address": "0x" + "a" * 40,
            "private_key": "0x" + "b" * 64,
        }
        svc = WalletService()
        result = svc.create_wallet()
        mock_create.assert_called_once()
        assert result["address"].startswith("0x")
        assert result["private_key"].startswith("0x")

    @patch("arc_devkit.core.wallet.get_balance")
    def test_get_native_balance(self, mock_balance):
        mock_balance.return_value = {
            "address": "0x" + "a" * 40,
            "balance_wei": "100000000000000000000",
            "balance_usdc": Decimal("100"),
        }
        svc = WalletService()
        result = svc.get_native_balance("0x" + "a" * 40)
        assert "balance_usdc" in result
