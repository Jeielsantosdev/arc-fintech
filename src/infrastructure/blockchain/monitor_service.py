"""Monitor service — uses arc_devkit AsyncMonitorAgent (v0.4.1+)."""

import asyncio
import logging
from collections.abc import AsyncGenerator, Callable

from src.config import settings

logger = logging.getLogger(__name__)


class AsyncMonitorService:
    """
    Monitors Arc wallet addresses for USDC events using async primitives.

    Arc DevKit components used:
      - arc_devkit.agents.async_monitor.AsyncMonitorAgent
        • execute()      — async monitoring loop (asyncio-native, no threads)
        • event_stream() — async generator for WebSocket / SSE feeds
        • get_balance()  — current balances for all watched addresses
    """

    def _agent(
        self,
        addresses: list[str],
        webhook_url: str | None = None,
        interval_seconds: int = 15,
    ):
        from arc_devkit.agents.async_monitor import AsyncMonitorAgent

        return AsyncMonitorAgent(
            watched_addresses=addresses,
            interval_seconds=interval_seconds,
            usdc_contract_address=settings.usdc_contract_address,
            webhook_url=webhook_url,
            rpc_url=settings.arc_rpc_url,
        )

    async def watch_address(
        self,
        address: str,
        webhook_url: str | None = None,
        callback: Callable[[dict], None] | None = None,
        interval_seconds: int = 15,
    ) -> dict:
        """
        Start async monitoring for an address.

        Schedules AsyncMonitorAgent.execute() as a background asyncio Task —
        no threads, no blocking. The task runs for the lifetime of the process.
        """
        agent = self._agent([address], webhook_url=webhook_url, interval_seconds=interval_seconds)
        asyncio.create_task(
            agent.execute(callback=callback, max_iterations=0),
            name=f"monitor-{address[:10]}",
        )
        logger.info("AsyncMonitorAgent task created for %s", address)
        return {"status": "watching", "address": address}

    async def watch_invoice_payment(
        self,
        invoice_id: str,
        recipient_address: str,
        on_payment: Callable[[dict], None],
        webhook_url: str | None = None,
        max_iterations: int = 60,
    ) -> dict:
        """
        Watch for a USDC credit to the invoice recipient (up to max_iterations polls).

        Uses AsyncMonitorAgent with a filtered callback — fires on_payment once
        an erc20_transfer credit is detected, then the task expires naturally.
        """
        agent = self._agent(
            [recipient_address],
            webhook_url=webhook_url,
            interval_seconds=10,
        )

        async def _async_handler(event: dict) -> None:
            if event.get("event_type") == "erc20_transfer" and event.get("type") == "credit":
                logger.info("Invoice %s: USDC credit detected on %s", invoice_id, recipient_address)
                if asyncio.iscoroutinefunction(on_payment):
                    await on_payment(event)
                else:
                    on_payment(event)

        asyncio.create_task(
            agent.execute(callback=_async_handler, max_iterations=max_iterations),
            name=f"invoice-{invoice_id[:8]}",
        )
        return {"status": "watching", "invoice_id": invoice_id, "address": recipient_address}

    async def event_stream(
        self,
        addresses: list[str],
        interval_seconds: int = 10,
    ) -> AsyncGenerator[dict, None]:
        """
        Async generator yielding blockchain events — designed for WebSocket / SSE endpoints.

        Uses AsyncMonitorAgent.event_stream() directly: each yielded dict
        is an event (balance change or erc20_transfer).
        """
        agent = self._agent(addresses, interval_seconds=interval_seconds)
        async for event in agent.event_stream():
            yield event

    async def get_balances(self, addresses: list[str]) -> dict:
        """Fetch current native + USDC balances for a list of addresses."""
        agent = self._agent(addresses)
        return agent.get_balance()
