"""Use case: get wallet balance (native ARC + USDC)."""

from src.domain.repositories.wallet_repo import AbstractWalletRepository
from src.infrastructure.blockchain.wallet_service import WalletService


class GetBalanceUseCase:
    def __init__(
        self,
        wallet_repo: AbstractWalletRepository,
        blockchain: WalletService,
    ) -> None:
        self._repo = wallet_repo
        self._blockchain = blockchain

    def execute(self, address: str) -> dict:
        # Arc DevKit: arc_devkit.core.wallet.get_balance + USDCToken.balance
        return self._blockchain.get_full_balance(address)

    def by_wallet_id(self, wallet_id: str) -> dict:
        wallet = self._repo.find_by_id(wallet_id)
        if not wallet:
            raise ValueError(f"Wallet {wallet_id} not found")
        return self.execute(wallet.address)
