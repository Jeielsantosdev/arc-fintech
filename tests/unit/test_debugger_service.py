"""Unit tests for TxDebuggerService — mocks arc_devkit TxAnalyzer."""

from unittest.mock import MagicMock, patch


class TestTxDebuggerService:
    @patch("arc_devkit.debugger.tx_analyzer.TxAnalyzer")
    def test_analyze_delegates_to_tx_analyzer(self, MockAnalyzer):
        expected = {
            "tx_hash": "0x" + "a" * 64,
            "status": "failed",
            "ai_summary": "Transaction reverted due to insufficient allowance.",
            "revert_reason": "ERC20: insufficient allowance",
            "gas_used": 21000,
            "cost_usdc": "0.000021",
        }
        instance = MockAnalyzer.return_value
        instance.analyze.return_value = expected

        from src.infrastructure.blockchain.debugger_service import TxDebuggerService

        svc = TxDebuggerService()
        result = svc.analyze("0x" + "a" * 64)

        instance.analyze.assert_called_once_with("0x" + "a" * 64)
        assert result["status"] == "failed"
        assert result["revert_reason"] == "ERC20: insufficient allowance"

    @patch("arc_devkit.debugger.tx_analyzer.TxAnalyzer")
    def test_analyze_batch_delegates_to_tx_analyzer(self, MockAnalyzer):
        tx_hashes = ["0x" + "a" * 64, "0x" + "b" * 64]
        expected = [
            {"tx_hash": tx_hashes[0], "status": "success"},
            {"tx_hash": tx_hashes[1], "status": "failed", "revert_reason": "Overflow"},
        ]
        instance = MockAnalyzer.return_value
        instance.analyze_batch.return_value = expected

        from src.infrastructure.blockchain.debugger_service import TxDebuggerService

        svc = TxDebuggerService()
        results = svc.analyze_batch(tx_hashes)

        instance.analyze_batch.assert_called_once_with(tx_hashes)
        assert len(results) == 2
        assert results[1]["revert_reason"] == "Overflow"

    @patch("arc_devkit.debugger.tx_analyzer.TxAnalyzer")
    def test_analyze_successful_tx(self, MockAnalyzer):
        expected = {
            "tx_hash": "0x" + "c" * 64,
            "status": "success",
            "ai_summary": "USDC transfer of 100 completed successfully.",
            "gas_used": 65000,
            "cost_usdc": "0.000065",
        }
        MockAnalyzer.return_value.analyze.return_value = expected

        from src.infrastructure.blockchain.debugger_service import TxDebuggerService

        result = TxDebuggerService().analyze("0x" + "c" * 64)
        assert result["status"] == "success"
        assert "revert_reason" not in result
