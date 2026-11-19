"""Safety tools: confirm destructive operations and read audit log."""

from __future__ import annotations

import logging
from typing import Any

import httpx
from fastmcp import FastMCP

from ..client import _build_headers, parse_stream_response, require_client
from ..safety import (
    ToolClass,
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
                            token,
                            entry["target"],
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
            body = entry.get("body")
            encoding = entry.get("encoding", "json")
            if body is not None:
                if encoding == "multipart":
                    # Plain text form fields: (None, value) tuples have no
                    # filename, so httpx encodes them as multipart/form-data
                    # text parts.  Do not set Content-Type — httpx must
                    # generate the boundary.
                    kwargs["files"] = {k: (None, str(v)) for k, v in body.items()}
                else:
                    kwargs["json"] = body
            if entry.get("params") is not None:
                kwargs["params"] = entry["params"]

            resp = await client.request(method, endpoint, headers=headers, **kwargs)
            resp.raise_for_status()
            if encoding == "stream":
                # Arcane action endpoints (e.g. /system/upgrade) answer with
                # newline-delimited JSON; resp.json() raises "Extra data".
                result = parse_stream_response(resp)
            else:
                result = resp.json()

            # A stream can complete transport-wise and still report a failure
            # inside its event payload; record that in the audit trail.
            stream_failed = encoding == "stream" and not result.get("success")
            audit_log.log_result(
                token=token,
                action=entry["action"],
                target=entry["target"],
                env_id=entry.get("env_id", "0"),
                success=not stream_failed,
                result=result,
                error=(result.get("error") or "stream reported failure") if stream_failed else None,
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
