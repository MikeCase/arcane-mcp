"""Safety tools: confirm destructive operations and read audit log."""

from __future__ import annotations

import logging
from typing import Any

import httpx
from fastmcp import FastMCP

from ..client import _build_headers, require_client
from ..safety import get_audit_log, get_token_store

logger = logging.getLogger(__name__)


def register(mcp: FastMCP) -> None:
    token_store = get_token_store()
    audit_log = get_audit_log()

    @mcp.tool()
    async def confirm_operation(token: str) -> Any:
        """Confirm and execute a destructive operation. Provide the ``confirmation_token`` that
        the earlier destructive tool call returned. The token expires after 120 seconds.

        Example flow:

        1. Agent calls ``remove_container("my-app")``
        2. Returns ``{"warning": "...", "confirmation_token": "abc123", ...}``
        3. Agent calls ``confirm_operation(token="abc123")``
        4. The operation executes and is logged to the audit trail.
        """
        entry = token_store.consume(token)
        if entry is None:
            return {
                "error": "Invalid or expired confirmation token. "
                "Tokens expire after 120 seconds. Request a new token by calling the destructive tool again.",
            }

        client = require_client()
        endpoint: str = entry["endpoint"]
        method: str = entry["method"]
        headers = _build_headers(entry.get("agent_token"))

        try:
            kwargs: dict[str, Any] = {}
            if entry.get("body") is not None:
                kwargs["json"] = entry["body"]
            if entry.get("params") is not None:
                kwargs["params"] = entry["params"]

            resp = await client.request(method, endpoint, headers=headers, **kwargs)
            resp.raise_for_status()
            result = resp.json()

            audit_log.log(
                action=entry["action"],
                target=entry["target"],
                env_id=entry.get("env_id", "0"),
                agent_token=entry.get("agent_token"),
                result=result,
            )
            return result

        except httpx.HTTPStatusError as e:
            logger.warning("HTTP %s on %s: %s", resp.status_code, endpoint, resp.text)
            return {"error": str(e), "status_code": resp.status_code, "detail": resp.text}
        except Exception as e:
            logger.exception("Unexpected error on %s", endpoint)
            return {"error": str(e)}

    @mcp.tool()
    async def read_audit_log(lines: int = 50) -> Any:
        """Read the last N lines of the audit log for destructive operations.

        The audit log records every destructive operation that was confirmed
        and executed, with timestamps, action type, target, and environment.
        """
        return audit_log.read_lines(lines)
