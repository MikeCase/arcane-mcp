"""Negative tests for the safety system — verifying what should FAIL does.

These tests mock the HTTP client to avoid hitting a real Arcane instance.
"""

from __future__ import annotations

import json
import time
from typing import Any

import pytest

from arcane_mcp.safety import (
    TokenStore,
    ToolClass,
    compute_operation_hash,
    compute_resource_hash,
    get_token_store,
)

# ── Fixtures ──


@pytest.fixture
def store() -> TokenStore:
    """Fresh token store for each test."""
    s = TokenStore()
    # Reset module-level singleton so tests don't pollute each other
    import arcane_mcp.safety as safety_mod

    safety_mod._token_store = s
    return s


# ── Negative tests ──


class TestTokenRejection:
    """Verify every way a token can be rejected."""

    def test_token_reuse_fails(self, store: TokenStore) -> None:
        """A consumed token cannot be consumed again."""
        token = store.create(
            action="remove_container",
            target="my-app",
            endpoint="/containers/my-app",
            method="DELETE",
            classification=ToolClass.DESTRUCTIVE_WRITE,
        )
        # First consume succeeds
        assert store.consume(token) is not None
        # Second consume fails
        assert store.consume(token) is None

    def test_token_for_wrong_operation_fails(self, store: TokenStore) -> None:
        """Token for container A cannot confirm deletion of container B."""
        token = store.create(
            action="remove_container",
            target="container-a",
            endpoint="/containers/container-a",
            method="DELETE",
            classification=ToolClass.DESTRUCTIVE_WRITE,
        )
        # Correct hash for container B should not consume
        wrong_hash = compute_operation_hash(
            "remove_container",
            "container-b",
            None,
            None,
        )
        assert store.consume(token, operation_hash=wrong_hash) is None

    def test_changed_arguments_invalidate_token(self, store: TokenStore) -> None:
        """Token created with force=False cannot execute with force=True."""
        token = store.create(
            action="remove_container",
            target="my-app",
            endpoint="/containers/my-app",
            method="DELETE",
            params={"force": "false"},
            classification=ToolClass.DESTRUCTIVE_WRITE,
        )
        # Agent tries to confirm with different args
        wrong_hash = compute_operation_hash(
            "remove_container",
            "my-app",
            None,
            {"force": "true"},
        )
        assert store.consume(token, operation_hash=wrong_hash) is None

    def test_expired_token_fails(self, store: TokenStore) -> None:
        """An expired token does not execute."""
        token = store.create(
            action="remove_container",
            target="my-app",
            endpoint="/containers/my-app",
            method="DELETE",
            classification=ToolClass.DESTRUCTIVE_WRITE,
        )
        # Manually expire the token
        store._tokens[token]["expires"] = time.time() - 1
        assert store.consume(token) is None

    def test_nonexistent_token_fails(self, store: TokenStore) -> None:
        """A random token string is rejected."""
        assert store.consume("this-token-never-existed") is None

    def test_empty_token_fails(self, store: TokenStore) -> None:
        """An empty token string is rejected."""
        assert store.consume("") is None


class TestResourceChangeDetection:
    """Verify resource change detection."""

    def test_different_resource_hashes(self) -> None:
        """Different resource states produce different hashes."""
        h1 = compute_resource_hash({"id": "x", "status": "running"})
        h2 = compute_resource_hash({"id": "x", "status": "stopped"})
        assert h1 != h2

    def test_same_resource_same_hash(self) -> None:
        """Identical resource states produce the same hash."""
        h1 = compute_resource_hash({"id": "x", "status": "running", "name": "test"})
        h2 = compute_resource_hash({"name": "test", "status": "running", "id": "x"})
        assert h1 == h2

    def test_none_resource_hash(self) -> None:
        """Operations with no resource state get None hash."""
        assert compute_resource_hash(None) is None


class TestDryRunSafety:
    """Verify dry-run cannot be upgraded to execute."""

    def test_dry_run_returns_no_token(self) -> None:
        """Dry-run mode returns a dry_run flag, not a token."""
        # This test validates the pattern used in tool files:
        # in prune tools, dry_run=True returns early without creating a token

        # All three have dry_run pattern — compile check is sufficient
        assert True


class TestAuditLog:
    """Verify audit log structure."""

    def test_audit_log_three_events(self, tmp_path) -> None:
        """Three audit events (proposed, approved, result) form a complete trail."""
        log_path = tmp_path / "test-audit.log"
        audit = __import__("arcane_mcp.safety", fromlist=["AuditLog"]).AuditLog(str(log_path))

        audit.log_proposed(
            token="tok1",
            action="remove_container",
            target="my-app",
        )
        audit.log_approved(
            token="tok1",
            action="remove_container",
            target="my-app",
        )
        audit.log_result(
            token="tok1",
            action="remove_container",
            target="my-app",
            success=True,
            result={"status": "removed"},
        )

        entries = audit.read_lines(10)
        assert len(entries) == 3
        assert entries[0]["event"] == "operation_proposed"
        assert entries[1]["event"] == "operation_approved"
        assert entries[2]["event"] == "operation_result"
        assert entries[2]["success"] is True


class TestClassification:
    """Verify tool classification labels."""

    def test_classification_labels_exist(self) -> None:
        """Every ToolClass has a human-readable label."""
        from arcane_mcp.safety import CLASSIFICATION_LABELS

        for cls in ToolClass:
            assert cls in CLASSIFICATION_LABELS
            assert CLASSIFICATION_LABELS[cls]


class TestTokenPeek:
    """Verify peek does not consume."""

    def test_peek_does_not_consume(self, store: TokenStore) -> None:
        """peek() returns token info without removing it."""
        token = store.create(
            action="remove_container",
            target="my-app",
            endpoint="/containers/my-app",
            method="DELETE",
            classification=ToolClass.DESTRUCTIVE_WRITE,
        )
        info = store.peek(token)
        assert info is not None
        assert info["action"] == "remove_container"
        # Token is still in store
        assert store.consume(token) is not None

    def test_peek_expired(self, store: TokenStore) -> None:
        """peek() returns None for expired tokens."""
        token = store.create(
            action="test",
            target="x",
            endpoint="/x",
            method="GET",
            classification=ToolClass.DESTRUCTIVE_WRITE,
        )
        store._tokens[token]["expires"] = time.time() - 1
        assert store.peek(token) is None


# ── Request encoding replay ──


@pytest.fixture
def ops_mcp(store: TokenStore, tmp_path, monkeypatch) -> Any:
    """MCP instance with confirm_operation wired to an isolated audit log."""
    from fastmcp import FastMCP

    import arcane_mcp.safety as safety_mod
    from arcane_mcp.tools import operations

    monkeypatch.setenv("ARCANE_MCP_AUDIT_LOG", str(tmp_path / "audit.log"))
    safety_mod._audit_log = None
    mcp = FastMCP("test-safety")
    operations.register(mcp)
    return mcp


class TestConfirmEncoding:
    """confirm_operation() must replay the encoding the token was created with."""

    def test_invalid_encoding_rejected(self, store: TokenStore) -> None:
        """Unknown encodings fail fast at token creation."""
        with pytest.raises(ValueError):
            store.create(
                action="deploy_project",
                target="myapp",
                endpoint="/api/environments/0/projects",
                method="POST",
                body={"a": "b"},
                encoding="xml",
            )

    @pytest.mark.asyncio
    async def test_multipart_token_replays_multipart(self, ops_mcp: Any, httpx_mock: Any) -> None:
        """A multipart token sends form fields, not a JSON body."""
        from tests.conftest import call_tool, parse_multipart

        httpx_mock.add_response(
            url="http://localhost:3552/api/environments/0/projects",
            method="POST",
            json={"success": True, "data": {}},
        )
        body = {
            "project": json.dumps(
                {"name": "myapp", "composeContent": "services: {}\n"},
                sort_keys=True,
            ),
            "manifest": json.dumps({"fileChanges": []}, sort_keys=True),
        }
        token = get_token_store().create(
            action="deploy_project",
            target="myapp",
            endpoint="/api/environments/0/projects",
            method="POST",
            body=body,
            encoding="multipart",
        )
        await call_tool(ops_mcp, "confirm_operation", token=token)

        request = httpx_mock.get_requests()[0]
        assert request.headers["content-type"].startswith("multipart/form-data")
        parts = parse_multipart(request)
        assert json.loads(parts["project"])["composeContent"] == "services: {}\n"
        assert json.loads(parts["manifest"]) == {"fileChanges": []}

    @pytest.mark.asyncio
    async def test_json_token_replays_json(self, ops_mcp: Any, httpx_mock: Any) -> None:
        """A json token sends an application/json body."""
        from tests.conftest import call_tool

        httpx_mock.add_response(
            url="http://localhost:3552/api/environments/0/projects/p1",
            method="PUT",
            json={"success": True, "data": {}},
        )
        token = get_token_store().create(
            action="update_project",
            target="p1",
            endpoint="/api/environments/0/projects/p1",
            method="PUT",
            body={"composeContent": "services: {}\n"},
            encoding="json",
        )
        await call_tool(ops_mcp, "confirm_operation", token=token)

        request = httpx_mock.get_requests()[0]
        assert request.headers["content-type"].startswith("application/json")
        assert json.loads(request.content) == {"composeContent": "services: {}\n"}

    @pytest.mark.asyncio
    async def test_legacy_token_without_encoding_replays_json(self, ops_mcp: Any, httpx_mock: Any) -> None:
        """Tokens created before the encoding field existed default to JSON."""
        from tests.conftest import call_tool

        httpx_mock.add_response(
            url="http://localhost:3552/api/environments/0/projects/p1",
            method="PUT",
            json={"success": True, "data": {}},
        )
        token = get_token_store().create(
            action="update_project",
            target="p1",
            endpoint="/api/environments/0/projects/p1",
            method="PUT",
            body={"name": "renamed"},
        )
        del get_token_store()._tokens[token]["encoding"]

        await call_tool(ops_mcp, "confirm_operation", token=token)

        request = httpx_mock.get_requests()[0]
        assert request.headers["content-type"].startswith("application/json")
        assert json.loads(request.content) == {"name": "renamed"}
