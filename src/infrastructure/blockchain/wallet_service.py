"""Blockchain wallet service — wraps arc_devkit.core.wallet + USDCToken."""

import logging
from decimal import Decimal

from cryptography.fernet import Fernet

from src.config import settings

logger = logging.getLogger(__name__)


def _fernet() -> Fernet:
    key = settings.key_encryption_secret.encode()
    return Fernet(key)


def encrypt_private_key(private_key: str) -> str:
    """Encrypt a private key with Fernet before persisting."""
    return _fernet().encrypt(private_key.encode()).decode()


def decrypt_private_key(encrypted: str) -> str:
    """Decrypt a stored private key."""
    return _fernet().decrypt(encrypted.encode()).decode()


class WalletService:
    """
    Uses arc_devkit.core.wallet and arc_devkit.usdc.token.USDCToken.

    Arc DevKit components:
      - arc_devkit.core.wallet.create_wallet()   → generate EVM keypair
      - arc_devkit.core.wallet.get_balance()     → native ARC balance
      - arc_devkit.usdc.token.USDCToken.balance() → USDC ERC-20 balance
      - arc_devkit.analytics.portfolio.PortfolioAnalyzer → tx history
    """

    def create_wallet(self) -> dict:
        """
        Generate a new EVM wallet via arc_devkit.

        Returns raw address and private key (caller must encrypt before storage).
        """
        from arc_devkit.core.wallet import create_wallet
        return create_wallet()

    def get_native_balance(self, address: str) -> dict:
        """Return native ARC balance via arc_devkit."""
        from arc_devkit.core.wallet import get_balance
        return get_balance(address)

    def get_usdc_balance(self, address: str) -> Decimal:
        """Return USDC ERC-20 balance via USDCToken."""
        from arc_devkit.usdc.token import USDCToken
        usdc = USDCToken(contract_address=settings.usdc_contract_address)
        try:
            return usdc.balance(address)
        except Exception as exc:
            logger.warning("USDC balance unavailable for %s: %s", address, exc)
            return Decimal("0")

    def get_full_balance(self, address: str) -> dict:
        """Combined native + USDC balance."""
        native = self.get_native_balance(address)
        usdc = self.get_usdc_balance(address)
        return {
            "address": address,
            "native_balance": native.get("balance_usdc", "0"),
            "usdc_balance": str(usdc),
        }

    def get_transaction_history(self, address: str, scan_blocks: int = 100) -> dict:
        """
        Use arc_devkit PortfolioAnalyzer to fetch on-chain transaction history.
        """
        from arc_devkit.analytics.portfolio import PortfolioAnalyzer
        analyzer = PortfolioAnalyzer(usdc_contract=settings.usdc_contract_address)
        snapshot = analyzer.analyze(address, scan_blocks=scan_blocks)
        return analyzer.to_dict(snapshot)
