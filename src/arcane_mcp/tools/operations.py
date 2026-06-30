"""Safety tools: confirm destructive operations and read audit log."""

from __future__ import annotations

import logging
from typing import Any

import httpx
from fastmcp import FastMCP

from ..client import _build_headers, require_client
from ..safety import (
    ToolClass,
    compute_operation_hash,
    compute_resource_hash,
    get_audit_log,
    get_token_store,
)

logger = logging.getLogger(__name__)


def register(mcp: FastMCP) -> None:
    token_store = get_token_store()
    audit_log = get_audit_log()

    @mcp.tool()
    async def confirm_operation(token: str, operation_hash: str | None = None) -> Any:
        """Confirm and execute a destructive operation.

        Provide the ``confirmation_token`` that the earlier destructive tool
        call returned, and optionally the ``operation_hash`` for strongest
        safety.  The token expires after 120 seconds.

        When ``operation_hash`` is provided it MUST match the hash returned
        by the destructive tool.  This prevents a token obtained for

            remove_container("my-app")

        from being used to execute

            remove_container("other-app").

        If the target resource supports it, the server will also check
        whether the resource has changed since the token was issued.
        If it has, the confirmation is denied.
        """
        # Validate token
        entry = token_store.consume(token, operation_hash=operation_hash)
        if entry is None:
            return {
                "error": "Invalid or expired confirmation token. "
                "If operation_hash was provided, it may not match. "
                "Tokens expire after 120 seconds. "
                "Request a new token by calling the destructive tool again.",
            }

        audit_log.log_approved(
            token=token,
            action=entry["action"],
            target=entry["target"],
            env_id=entry.get("env_id", "0"),
        )

        # Resource change detection — re-fetch and compare hashes
        stored_resource_hash = entry.get("resource_hash")
        if stored_resource_hash is not None:
            try:
                client = require_client()
                inspect_endpoint = entry.get("inspect_endpoint", entry["endpoint"].rstrip("/"))
                inspect_resp = await client.get(
                    inspect_endpoint,
                    headers=_build_headers(entry.get("agent_token")),
                )
                if inspect_resp.status_code < 500:
                    fresh_hash = compute_resource_hash(inspect_resp.json())
                    if fresh_hash is not None and fresh_hash != stored_resource_hash:
                        logger.warning(
                            "Token %s: resource %s changed since proposal",
                            token, entry["target"],
                        )
                        return {
                            "error": "Resource state has changed since the "
                            f"confirmation token was created. "
                            f"The target {entry['target']} was modified between "
                            f"the proposal and this confirmation. "
                            f"Call the destructive tool again to create a fresh token.",
                            "action": entry["action"],
                            "target": entry["target"],
                        }
            except Exception as e:
                logger.debug("Resource change check skipped for %s: %s", entry["target"], e)

        # Execute
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

            audit_log.log_result(
                token=token,
                action=entry["action"],
                target=entry["target"],
                env_id=entry.get("env_id", "0"),
                success=True,
                result=result,
            )
            return result

        except httpx.HTTPStatusError as e:
            logger.warning("HTTP %s on %s: %s", resp.status_code, endpoint, resp.text)
            audit_log.log_result(
                token=token,
                action=entry["action"],
                target=entry["target"],
                env_id=entry.get("env_id", "0"),
                success=False,
                error=f"HTTP {resp.status_code}: {resp.text}",
            )
            return {"error": str(e), "status_code": resp.status_code, "detail": resp.text}
        except Exception as e:
            logger.exception("Unexpected error on %s", endpoint)
            audit_log.log_result(
                token=token,
                action=entry["action"],
                target=entry["target"],
                env_id=entry.get("env_id", "0"),
                success=False,
                error=str(e),
            )
            return {"error": str(e)}

    @mcp.tool()
    async def read_audit_log(lines: int = 50, event_type: str | None = None) -> Any:
        """Read the last N lines of the audit log for destructive operations.

        Parameters
        ----------
        lines:
            Number of most recent log entries to return.
        event_type:
            Optional filter: ``operation_proposed``, ``operation_approved``,
            or ``operation_result``.  When omitted, returns all events.
        """
        entries = audit_log.read_lines(lines)
        if event_type:
            entries = [e for e in entries if e.get("event") == event_type]
        return entries

    @mcp.tool()
    async def get_operation_status(token: str) -> Any:
        """Check whether a confirmation token is still valid without consuming it.

        Returns the operation details (minus sensitive fields) or an error
        if the token is invalid or expired.
        """
        entry = token_store.peek(token)
        if entry is None:
            return {
                "error": "Token not found or expired.",
                "token": token,
                "valid": False,
            }
        return {
            "token": token,
            "valid": True,
            "expires_in_seconds": max(0, int(entry["expires"] - __import__("time").time())),
            "action": entry["action"],
            "target": entry["target"],
            "classification": entry.get("classification", ToolClass.DESTRUCTIVE_WRITE),
            "operation_hash": entry.get("operation_hash"),
        }

    @mcp.tool()
    async def classify_tool(
        action: str,
        classification: str = ToolClass.DESTRUCTIVE_WRITE,
    ) -> Any:
        """Return the classification label for a given tool classification value."""
        from ..safety import CLASSIFICATION_LABELS
        return {
            "classification": classification,
            "label": CLASSIFICATION_LABELS.get(ToolClass(classification), "Unknown"),
        }
