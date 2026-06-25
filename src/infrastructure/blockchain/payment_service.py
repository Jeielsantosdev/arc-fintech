"""Payment service — uses arc_devkit PaymentAgent and USDCToken."""

import logging
from decimal import Decimal

from src.config import settings

logger = logging.getLogger(__name__)


class PaymentService:
    """
    Executes USDC payments on Arc via arc_devkit.

    Arc DevKit components used:
      - arc_devkit.agents.payment_agent.PaymentAgent.execute(token="usdc")
      - arc_devkit.agents.payment_agent.PaymentAgent.execute_batch()
      - arc_devkit.usdc.token.USDCToken.transfer()
    """

    def _agent(self, private_key: str | None = None):
        """Build a PaymentAgent with the given or platform private key."""
        from arc_devkit.agents.payment_agent import PaymentAgent
        key = private_key or settings.arc_private_key
        return PaymentAgent(private_key=key, rpc_url=settings.arc_rpc_url)

    def send_usdc(
        self,
        to: str,
        amount_usdc: Decimal,
        private_key: str | None = None,
        broadcast: bool = True,
        wait_receipt: bool = True,
        on_success=None,
        on_failure=None,
    ) -> dict:
        """
        Send USDC to a recipient.

        Uses PaymentAgent.execute(token="usdc", enviar=broadcast).
        Returns the full receipt dict from arc_devkit.
        """
        agent = self._agent(private_key)
        result = agent.execute(
            to=to,
            amount_usdc=float(amount_usdc),
            enviar=broadcast,
            wait_receipt=wait_receipt,
            on_success=on_success,
            on_failure=on_failure,
            token="usdc",
        )
        logger.info(
            "Payment %s → %s: %s USDC | status=%s | tx=%s",
            agent.wallet_address,
            to,
            amount_usdc,
            result.get("status"),
            result.get("tx_hash", "—"),
        )
        return result

    def send_batch(self, payments: list[dict], broadcast: bool = True) -> list[dict]:
        """
        Execute multiple USDC payments in a single batch.

        Each item in payments: {"to": address, "amount_usdc": float, "enviar": bool}

        Uses PaymentAgent.execute_batch() with incremental nonces.
        """
        agent = self._agent()
        enriched = [
            {"to": p["to"], "amount_usdc": float(p["amount_usdc"]), "enviar": broadcast}
            for p in payments
        ]
        results = agent.execute_batch(enriched)
        logger.info("Batch payment: %d transfers processed.", len(results))
        return results

    def estimate_gas(self, to: str, amount_usdc: float) -> dict:
        """Return gas estimate for a transfer."""
        from arc_devkit.core.gas import estimate_transfer
        return estimate_transfer(
            to=to,
            amount_usdc=amount_usdc,
            from_address=settings.platform_wallet_address or None,
        )

    def execute_split(
        self,
        recipients: list[dict],
        broadcast: bool = True,
    ) -> list[dict]:
        """
        Execute a split payment to multiple addresses.

        recipients: [{"to": address, "amount_usdc": Decimal, "label": str}]
        Returns list of per-recipient results.
        """
        payments = [
            {"to": r["to"], "amount_usdc": float(r["amount_usdc"]), "enviar": broadcast}
            for r in recipients
        ]
        return self.send_batch(payments, broadcast=broadcast)
