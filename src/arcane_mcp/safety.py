"""Safety primitives: confirmation tokens, audit logging, dry-run tracking."""

from __future__ import annotations

import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

_TOKEN_TTL = 120  # seconds

# ── Confirmation Token Store ──


class TokenStore:
    """Store of one-time confirmation tokens with TTL.

    Each token stores enough info to reconstruct the HTTP call when
    ``confirm_operation()`` is called.
    """

    def __init__(self) -> None:
        self._tokens: dict[str, dict[str, Any]] = {}

    def create(
        self,
        action: str,
        target: str,
        endpoint: str,
        method: str = "POST",
        body: dict[str, Any] | None = None,
        params: dict[str, str] | None = None,
        env_id: str = "0",
        agent_token: str | None = None,
    ) -> str:
        """Create a confirmation token and store the operation details.

        Returns the hex token string that the agent must pass to
        ``confirm_operation()``.
        """
        token = uuid.uuid4().hex[:12]
        self._tokens[token] = {
            "action": action,
            "target": target,
            "endpoint": endpoint,
            "method": method.upper(),
            "body": body,
            "params": params,
            "env_id": env_id,
            "agent_token": agent_token,
            "expires": time.time() + _TOKEN_TTL,
        }
        logger.info("Created confirmation token %s for %s on %s", token, action, target)
        return token

    def consume(self, token: str) -> dict[str, Any] | None:
        """Retrieve and remove a token's data.

        Returns ``None`` if the token is invalid or expired.
        """
        entry = self._tokens.pop(token, None)
        if entry is None:
            return None
        if time.time() > entry["expires"]:
            logger.warning("Expired confirmation token %s", token)
            return None
        return entry

    def __len__(self) -> int:
        # Prune expired tokens
        now = time.time()
        expired = [t for t, e in self._tokens.items() if now > e["expires"]]
        for t in expired:
            del self._tokens[t]
        return len(self._tokens)


# ── Audit Log ──


class AuditLog:
    """Structured JSON-lines audit log for destructive operations."""

    def __init__(self, path: str | None = None) -> None:
        self.path = (
            path
            or os.environ.get("ARCANE_MCP_AUDIT_LOG")
            or os.path.expanduser("~/.arcane-mcp-audit.log")
        )

    def log(
        self,
        action: str,
        target: str,
        env_id: str = "0",
        agent_token: str | None = None,
        result: Any = None,
    ) -> None:
        """Append one audit entry as a JSON line."""
        entry: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "target": target,
            "env_id": env_id,
        }
        if result is not None:
            entry["result"] = result
        try:
            with open(self.path, "a") as f:
                f.write(json.dumps(entry) + "\n")
            logger.info("Audit: %s %s env=%s", action, target, env_id)
        except OSError as e:
            logger.warning("Failed to write audit log to %s: %s", self.path, e)

    def read_lines(self, n: int = 50) -> list[dict[str, Any]]:
        """Return the last *n* audit log entries."""
        try:
            with open(self.path) as f:
                lines = f.readlines()
        except (OSError, FileNotFoundError):
            return []
        entries: list[dict[str, Any]] = []
        for line in lines[-n:]:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    entries.append({"raw": line})
        return entries


# ── Module-level singletons ──

_token_store: TokenStore | None = None
_audit_log: AuditLog | None = None


def get_token_store() -> TokenStore:
    """Return the module-level token store singleton."""
    global _token_store
    if _token_store is None:
        _token_store = TokenStore()
    return _token_store


def get_audit_log() -> AuditLog:
    """Return the module-level audit log singleton."""
    global _audit_log
    if _audit_log is None:
        _audit_log = AuditLog()
    return _audit_log
