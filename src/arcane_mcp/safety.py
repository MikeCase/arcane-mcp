"""Safety primitives: confirmation tokens, operation hashing, resource change detection,
three-event audit logging, tool classification, and structured dry-run output."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)

_TOKEN_TTL = 120          # seconds before a token expires
_POLICY_VERSION = "1.0.0"  # bumped when safety semantics change

# ── Tool Classification ──


class ToolClass(str, Enum):
    READ = "read"
    REVERSIBLE_WRITE = "reversible_write"
    DESTRUCTIVE_WRITE = "destructive_write"
    CREDENTIAL_SENSITIVE = "credential_sensitive"


CLASSIFICATION_LABELS = {
    ToolClass.READ: "Read-only — no side effects",
    ToolClass.REVERSIBLE_WRITE: "Reversible write — start/stop/restart",
    ToolClass.DESTRUCTIVE_WRITE: "Destructive — requires two-step confirmation",
    ToolClass.CREDENTIAL_SENSITIVE: "Credential/secret-bearing — log separate from config",
}

# ── Operation Hash ──


def compute_operation_hash(
    action: str,
    target: str,
    body: dict[str, Any] | None = None,
    params: dict[str, str] | None = None,
) -> str:
    """Deterministic hash of the full operation parameters.

    This binds the confirmation token to the exact operation, resource,
    and normalized arguments.  ``confirm_operation()`` requires the agent
    to re-submit this hash so that a token for
    ``remove_container("my-app")`` cannot be used to remove
    ``my-other-app``.
    """
    raw = json.dumps(
        {
            "action": action,
            "target": target,
            "body": body if body else {},
            "params": params if params else {},
        },
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def compute_resource_hash(
    resource_state: dict[str, Any] | None,
) -> str | None:
    """Hash of the current resource state at proposal time.

    ``confirm_operation()`` re-queries the resource and compares this hash.
    If they differ the resource changed and the confirmation is denied.
    Returns ``None`` when the resource has no observable state
    (e.g. a ``prune`` operation).
    """
    if resource_state is None:
        return None
    raw = json.dumps(resource_state, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


# ── Confirmation Token Store ──


class TokenStore:
    """Store of one-time confirmation tokens with TTL and operation binding.

    Each token stores the full operation details, a hash of the operation
    parameters, (optionally) a hash of the resource state at proposal time,
    a classification label, the caller/session identity, and the policy
    version.  ``confirm_operation()`` validates all of these before
    executing.
    """

    def __init__(self) -> None:
        self._tokens: dict[str, dict[str, Any]] = {}

    def create(
        self,
        *,
        action: str,
        target: str,
        endpoint: str,
        method: str = "POST",
        body: dict[str, Any] | None = None,
        params: dict[str, str] | None = None,
        env_id: str = "0",
        agent_token: str | None = None,
        classification: str = ToolClass.DESTRUCTIVE_WRITE,
        resource_hash: str | None = None,
    ) -> str:
        """Create a confirmation token bound to the exact operation.

        Parameters
        ----------
        classification:
            One of ``ToolClass`` values.
        resource_hash:
            Hash of the resource state at proposal time (see
            ``compute_resource_hash``).  When set, ``confirm_operation()``
            will re-fetch the resource and compare; a mismatch denies the
            confirmation.

        Returns the hex token string.
        """
        operation_hash = compute_operation_hash(action, target, body, params)
        session_id = agent_token or "local"
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
            "classification": classification,
            "operation_hash": operation_hash,
            "resource_hash": resource_hash,
            "session_id": session_id,
            "policy_version": _POLICY_VERSION,
            "expires": time.time() + _TOKEN_TTL,
        }
        logger.info(
            "Token %s: %s %s (op_hash=%s class=%s)",
            token, action, target, operation_hash, classification,
        )
        return token

    def consume(self, token: str, operation_hash: str | None = None) -> dict[str, Any] | None:
        """Retrieve and remove a token, optionally validating the operation hash.

        Parameters
        ----------
        operation_hash:
            Must match the stored hash when provided.  This is the key
            defence against token replay on a different operation.
        """
        entry = self._tokens.pop(token, None)
        if entry is None:
            logger.warning("Token %s not found (already consumed or never existed)", token)
            return None
        if time.time() > entry["expires"]:
            logger.warning("Token %s expired", token)
            return None
        if operation_hash is not None and entry["operation_hash"] != operation_hash:
            logger.warning(
                "Token %s operation_hash mismatch: got %s, expected %s",
                token, operation_hash, entry["operation_hash"],
            )
            return None
        return entry

    def peek(self, token: str) -> dict[str, Any] | None:
        """Look up a token without consuming it (for audit logging and dry-run display)."""
        entry = self._tokens.get(token)
        if entry is None:
            return None
        if time.time() > entry["expires"]:
            self._tokens.pop(token, None)
            return None
        return {k: v for k, v in entry.items() if k != "agent_token"}

    def __len__(self) -> int:
        now = time.time()
        expired = [t for t, e in self._tokens.items() if now > e["expires"]]
        for t in expired:
            del self._tokens[t]
        return len(self._tokens)


# ── Audit Log (three-event model) ──


class AuditLog:
    """Structured JSON-lines audit log for destructive operations.

    Every destructive operation emits three events:

    1. ``operation_proposed`` — when the token is created (before execution)
    2. ``operation_approved`` — when ``confirm_operation()`` is called
    3. ``operation_result`` — when the API call completes (success **or** failure)
    """

    def __init__(self, path: str | None = None) -> None:
        self.path = (
            path
            or os.environ.get("ARCANE_MCP_AUDIT_LOG")
            or os.path.expanduser("~/.arcane-mcp-audit.log")
        )

    def log_proposed(
        self,
        token: str,
        action: str,
        target: str,
        env_id: str = "0",
        agent_token: str | None = None,
        classification: str = ToolClass.DESTRUCTIVE_WRITE,
        operation_hash: str = "",
        resource_hash: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Event 1: operation was proposed (token created)."""
        entry: dict[str, Any] = {
            "event": "operation_proposed",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "token": token,
            "action": action,
            "target": target,
            "env_id": env_id,
            "classification": classification,
            "operation_hash": operation_hash,
            "policy_version": _POLICY_VERSION,
        }
        if resource_hash:
            entry["resource_hash"] = resource_hash
        if details:
            entry["details"] = details
        self._write(entry)

    def log_approved(
        self,
        token: str,
        action: str,
        target: str,
        env_id: str = "0",
    ) -> None:
        """Event 2: operation was approved (confirm_operation called)."""
        self._write({
            "event": "operation_approved",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "token": token,
            "action": action,
            "target": target,
            "env_id": env_id,
        })

    def log_result(
        self,
        token: str,
        action: str,
        target: str,
        env_id: str = "0",
        success: bool = True,
        result: Any = None,
        error: str | None = None,
    ) -> None:
        """Event 3: operation completed (success or failure)."""
        entry: dict[str, Any] = {
            "event": "operation_result",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "token": token,
            "action": action,
            "target": target,
            "env_id": env_id,
            "success": success,
        }
        if result is not None:
            entry["result"] = result
        if error:
            entry["error"] = error
        self._write(entry)

    def _write(self, entry: dict[str, Any]) -> None:
        try:
            with open(self.path, "a") as f:
                f.write(json.dumps(entry) + "\n")
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
    global _token_store
    if _token_store is None:
        _token_store = TokenStore()
    return _token_store


def get_audit_log() -> AuditLog:
    global _audit_log
    if _audit_log is None:
        _audit_log = AuditLog()
    return _audit_log
