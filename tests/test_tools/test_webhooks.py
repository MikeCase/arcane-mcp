"""Tests for webhook tools."""
from __future__ import annotations

from typing import Any

import pytest

from tests.conftest import call_tool


@pytest.mark.asyncio
async def test_trigger_webhook(mcp: Any, httpx_mock: Any) -> None:
    """trigger_webhook posts to the webhook endpoint."""
    httpx_mock.add_response(
        url="http://localhost:3552/api/webhooks/trigger/tok_abc",
        method="POST",
        json={"message": "triggered"},
    )
    result = await call_tool(mcp, "trigger_webhook", token="tok_abc", action="deploy")
    assert result == {"message": "triggered"}


@pytest.mark.asyncio
async def test_trigger_webhook_http_error(mcp: Any, httpx_mock: Any) -> None:
    """trigger_webhook returns error on failure."""
    httpx_mock.add_response(status_code=404)
    result = await call_tool(mcp, "trigger_webhook", token="tok_bad", action="deploy")
    assert "error" in result
