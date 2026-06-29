"""Webhook trigger tools."""
from __future__ import annotations

import logging
from typing import Any

import httpx
from fastmcp import FastMCP

from ..client import require_client

logger = logging.getLogger(__name__)


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    async def trigger_webhook(token: str, action: str) -> Any:
        """Trigger an Arcane inbound webhook by token."""
        client = require_client()
        url = f"/api/webhooks/trigger/{token}"
        body = {"action": action}
        try:
            resp = await client.post(url, json=body)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            logger.warning("HTTP %s on %s: %s", resp.status_code, url, resp.text)
            return {"error": str(e), "status_code": resp.status_code, "detail": resp.text}
        except Exception as e:
            logger.exception("Unexpected error on %s", url)
            return {"error": str(e)}
