"""Shared test fixtures for arcane-mcp tests."""
from __future__ import annotations

import json
from typing import Any

import pytest
from fastmcp import FastMCP

from arcane_mcp.tools import (
    containers,
    environments,
    images,
    networks,
    operations,
    projects,
    system,
    volumes,
    webhooks,
)


@pytest.fixture(autouse=True)
def setup_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set default env vars for all tests."""
    monkeypatch.setenv("ARCANE_BASE_URL", "http://localhost:3552")
    monkeypatch.setenv("ARCANE_API_KEY", "test-key-abc123")


@pytest.fixture(autouse=True)
def isolated_audit_log(monkeypatch: pytest.MonkeyPatch, tmp_path: Any) -> None:
    """Write the safety audit log to a temp file instead of ~/.arcane-mcp-audit.log."""
    import arcane_mcp.safety as safety_mod

    monkeypatch.setenv("ARCANE_MCP_AUDIT_LOG", str(tmp_path / "audit.log"))
    monkeypatch.setattr(safety_mod, "_audit_log", None)


@pytest.fixture
def mcp() -> FastMCP:
    """Return a FastMCP instance with all tools registered."""
    mcp = FastMCP("test-arcane")
    containers.register(mcp)
    environments.register(mcp)
    images.register(mcp)
    networks.register(mcp)
    operations.register(mcp)
    projects.register(mcp)
    system.register(mcp)
    volumes.register(mcp)
    webhooks.register(mcp)
    return mcp


async def call_tool(mcp: FastMCP, tool_name: str, **kwargs: Any) -> Any:
    """Call a registered MCP tool by name and return the raw result."""
    result = await mcp.call_tool(tool_name, kwargs)
    # ToolResult.content is a list of TextContent with .text as JSON
    if result.content and hasattr(result.content[0], "text"):
        return json.loads(result.content[0].text)
    return result.content
