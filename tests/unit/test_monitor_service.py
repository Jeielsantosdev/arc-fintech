"""Unit tests for AsyncMonitorService — mocks arc_devkit AsyncMonitorAgent."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestAsyncMonitorService:
    @patch("arc_devkit.agents.async_monitor.AsyncMonitorAgent")
    def test_agent_built_with_correct_params(self, MockAgent):
        from src.infrastructure.blockchain.monitor_service import AsyncMonitorService

        svc = AsyncMonitorService()
        svc._agent(["0x" + "a" * 40], webhook_url="http://hook.test", interval_seconds=5)
        MockAgent.assert_called_once()
        call_kwargs = MockAgent.call_args.kwargs
        assert call_kwargs["watched_addresses"] == ["0x" + "a" * 40]
        assert call_kwargs["interval_seconds"] == 5
        assert call_kwargs["webhook_url"] == "http://hook.test"

    @pytest.mark.asyncio
    @patch("src.infrastructure.blockchain.monitor_service.AsyncMonitorService._agent")
    async def test_get_balances_delegates_to_agent(self, mock_agent_factory):
        mock_agent = MagicMock()
        mock_agent.get_balance.return_value = {"0x" + "a" * 40: {"usdc": "100"}}
        mock_agent_factory.return_value = mock_agent

        from src.infrastructure.blockchain.monitor_service import AsyncMonitorService

        svc = AsyncMonitorService()
        result = await svc.get_balances(["0x" + "a" * 40])
        mock_agent.get_balance.assert_called_once()
        assert "0x" + "a" * 40 in result

    @pytest.mark.asyncio
    @patch("src.infrastructure.blockchain.monitor_service.asyncio.create_task")
    @patch("src.infrastructure.blockchain.monitor_service.AsyncMonitorService._agent")
    async def test_watch_address_creates_async_task(self, mock_agent_factory, mock_create_task):
        mock_agent = MagicMock()
        mock_agent.execute = AsyncMock(return_value={"iterations": 0})
        mock_agent_factory.return_value = mock_agent

        from src.infrastructure.blockchain.monitor_service import AsyncMonitorService

        svc = AsyncMonitorService()
        result = await svc.watch_address("0x" + "a" * 40)
        mock_create_task.assert_called_once()
        assert result["status"] == "watching"
        assert result["address"] == "0x" + "a" * 40

    @pytest.mark.asyncio
    @patch("src.infrastructure.blockchain.monitor_service.asyncio.create_task")
    @patch("src.infrastructure.blockchain.monitor_service.AsyncMonitorService._agent")
    async def test_watch_invoice_payment_creates_task(self, mock_agent_factory, mock_create_task):
        mock_agent = MagicMock()
        mock_agent.execute = AsyncMock(return_value={"iterations": 5})
        mock_agent_factory.return_value = mock_agent

        from src.infrastructure.blockchain.monitor_service import AsyncMonitorService

        on_payment = MagicMock()
        svc = AsyncMonitorService()
        result = await svc.watch_invoice_payment(
            invoice_id="inv-123",
            recipient_address="0x" + "b" * 40,
            on_payment=on_payment,
        )
        mock_create_task.assert_called_once()
        assert result["status"] == "watching"
        assert result["invoice_id"] == "inv-123"

    @pytest.mark.asyncio
    @patch("src.infrastructure.blockchain.monitor_service.AsyncMonitorService._agent")
    async def test_event_stream_yields_events(self, mock_agent_factory):
        async def _fake_stream():
            yield {"event_type": "erc20_transfer", "amount_usdc": "10.0"}
            yield {"event_type": "balance_change", "amount_usdc": "5.0"}

        mock_agent = MagicMock()
        mock_agent.event_stream.return_value = _fake_stream()
        mock_agent_factory.return_value = mock_agent

        from src.infrastructure.blockchain.monitor_service import AsyncMonitorService

        svc = AsyncMonitorService()
        events = []
        async for ev in svc.event_stream(["0x" + "a" * 40]):
            events.append(ev)

        assert len(events) == 2
        assert events[0]["event_type"] == "erc20_transfer"
        assert events[1]["event_type"] == "balance_change"
