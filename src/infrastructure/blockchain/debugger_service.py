"""Debugger service — uses arc_devkit TxAnalyzer (v0.4.1+)."""

import logging

from src.config import settings

logger = logging.getLogger(__name__)


class TxDebuggerService:
    """
    AI-powered transaction diagnosis via arc_devkit.

    Arc DevKit components used:
      - arc_devkit.debugger.tx_analyzer.TxAnalyzer
        • analyze(tx_hash)          — single tx: status, revert reason, AI summary, gas cost
        • analyze_batch(tx_hashes)  — multiple txs with optional progress callback
    """

    def _analyzer(self):
        from arc_devkit.debugger.tx_analyzer import TxAnalyzer
        return TxAnalyzer(rpc_url=settings.arc_rpc_url)

    def analyze(self, tx_hash: str) -> dict:
        """
        Fetch and diagnose a single transaction.

        Returns a dict with: tx_hash, status, ai_summary, gas_used,
        cost_usdc, revert_reason (if failed), decoded_input (if ABI available).
        """
        logger.info("Analyzing transaction %s", tx_hash)
        return self._analyzer().analyze(tx_hash)

    def analyze_batch(self, tx_hashes: list[str]) -> list[dict]:
        """
        Diagnose multiple transactions in sequence.

        Useful for auditing payroll runs or split disbursements where
        some payments may have failed with on-chain reverts.
        """
        logger.info("Batch-analyzing %d transactions", len(tx_hashes))
        return self._analyzer().analyze_batch(tx_hashes)
