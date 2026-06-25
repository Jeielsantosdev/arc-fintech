"""Use case: get transaction history for a wallet."""

from src.domain.repositories.transaction_repo import AbstractTransactionRepository
from src.infrastructure.blockchain.wallet_service import WalletService


class GetTransactionHistoryUseCase:
    def __init__(
        self,
        tx_repo: AbstractTransactionRepository,
        blockchain: WalletService,
    ) -> None:
        self._tx_repo = tx_repo
        self._blockchain = blockchain

    def execute(self, address: str, limit: int = 50, offset: int = 0) -> dict:
        # DB-recorded transactions (indexed, fast)
        db_txs = self._tx_repo.find_by_address(address, limit=limit, offset=offset)

        db_records = [
            {
                "id": tx.id,
                "tx_hash": tx.tx_hash,
                "from": tx.from_address,
                "to": tx.to_address,
                "amount_usdc": str(tx.amount_usdc),
                "type": tx.tx_type.value,
                "status": tx.status.value,
                "created_at": tx.created_at.isoformat(),
            }
            for tx in db_txs
        ]

        # On-chain scan via arc_devkit PortfolioAnalyzer (recent blocks)
        onchain = self._blockchain.get_transaction_history(address, scan_blocks=50)

        return {
            "address": address,
            "recorded": db_records,
            "onchain_scan": onchain,
        }
