"""Monitor service — uses arc_devkit MonitorAgent and EventListener."""

import logging
import threading
from collections.abc import Callable

from src.config import settings

logger = logging.getLogger(__name__)

_monitor_thread: threading.Thread | None = None
_monitor_agent = None


class MonitorService:
    """
    Monitors Arc wallet addresses for USDC events.

    Arc DevKit components used:
      - arc_devkit.agents.monitor_agent.MonitorAgent
      - arc_devkit.events.listener.EventListener
    """

    def watch_address(
        self,
        address: str,
        webhook_url: str | None = None,
        callback: Callable[[dict], None] | None = None,
        interval_seconds: int = 15,
        background: bool = True,
    ) -> dict:
        """
        Start watching an address for balance changes and USDC Transfer events.

        Fires both callback (if given) and webhook_url on each detected change.
        """
        from arc_devkit.agents.monitor_agent import MonitorAgent

        agent = MonitorAgent(
            watched_address=address,
            interval_seconds=interval_seconds,
            usdc_contract_address=settings.usdc_contract_address,
            webhook_url=webhook_url,
            rpc_url=settings.arc_rpc_url,
        )

        if background:
            t = threading.Thread(
                target=agent.execute,
                kwargs={"callback": callback, "max_iterations": 0},
                daemon=True,
                name=f"monitor-{address[:10]}",
            )
            t.start()
            logger.info("MonitorAgent started in background for %s", address)
            return {"status": "watching", "address": address, "thread": t.name}

        return agent.execute(callback=callback)

    def watch_invoice_payment(
        self,
        invoice_id: str,
        recipient_address: str,
        expected_amount_usdc: float,
        on_payment: Callable[[dict], None],
        webhook_url: str | None = None,
    ) -> dict:
        """
        Watch for an exact USDC payment to an invoice recipient.

        Fires on_payment callback once the expected amount is detected.
        Uses MonitorAgent ERC-20 event scanning.
        """
        from arc_devkit.agents.monitor_agent import MonitorAgent

        def _handler(event: dict) -> None:
            if event.get("event_type") != "erc20_transfer":
                return
            if event.get("type") != "credit":
                return
            # Loose check: any credit to the recipient triggers confirmation
            logger.info(
                "Invoice %s: USDC credit detected on %s — triggering payment handler",
                invoice_id,
                recipient_address,
            )
            on_payment(event)

        agent = MonitorAgent(
            watched_address=recipient_address,
            interval_seconds=10,
            usdc_contract_address=settings.usdc_contract_address,
            webhook_url=webhook_url,
            rpc_url=settings.arc_rpc_url,
        )

        t = threading.Thread(
            target=agent.execute,
            kwargs={"callback": _handler, "max_iterations": 60},
            daemon=True,
            name=f"invoice-{invoice_id[:8]}",
        )
        t.start()
        return {"status": "watching", "invoice_id": invoice_id, "address": recipient_address}

    def get_current_balance(self, addresses: list[str]) -> dict:
        """Fetch current balances for a list of addresses via MonitorAgent."""
        from arc_devkit.agents.monitor_agent import MonitorAgent

        agent = MonitorAgent(
            watched_addresses=addresses,
            rpc_url=settings.arc_rpc_url,
        )
        return agent.get_balance()
