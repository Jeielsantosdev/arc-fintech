"""Use case: create a new wallet for a user."""

import logging

from src.domain.entities.wallet import Wallet
from src.domain.repositories.wallet_repo import AbstractWalletRepository
from src.infrastructure.blockchain.wallet_service import WalletService, encrypt_private_key

logger = logging.getLogger(__name__)


class CreateWalletUseCase:
    """
    Generates an EVM keypair via arc_devkit.core.wallet.create_wallet(),
    encrypts the private key with Fernet, and persists the wallet.
    """

    def __init__(
        self,
        wallet_repo: AbstractWalletRepository,
        blockchain: WalletService,
    ) -> None:
        self._repo = wallet_repo
        self._blockchain = blockchain

    def execute(self, user_id: str) -> dict:
        # arc_devkit generates the keypair
        raw = self._blockchain.create_wallet()
        address = raw["address"]
        private_key = raw["private_key"]

        encrypted = encrypt_private_key(private_key)
        wallet = Wallet(user_id=user_id, address=address, encrypted_private_key=encrypted)
        saved = self._repo.save(wallet)

        logger.info("Wallet created for user %s: %s", user_id, address)
        return {
            "wallet_id": saved.id,
            "user_id": user_id,
            "address": address,
            "status": saved.status.value,
        }
