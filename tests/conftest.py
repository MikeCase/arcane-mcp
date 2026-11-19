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
    projects,
    system,
    volumes,
    webhooks,
)


@pytest.fixture(autouse=True)
def setup_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set default env vars for all tests.

    ``ARCANE_API_VERSION`` is pinned so route construction never probes
    ``GET /api/version``: tests must not touch the network, and an un-mocked
    probe would also consume the first ``httpx_mock`` response. Tests that
    exercise detection itself override it locally (see ``test_client.py``).
    """
    monkeypatch.setenv("ARCANE_BASE_URL", "http://localhost:3552")
    monkeypatch.setenv("ARCANE_API_KEY", "test-key-abc123")
    monkeypatch.setenv("ARCANE_API_VERSION", "2")


@pytest.fixture
def mcp() -> FastMCP:
    """Return a FastMCP instance with all tools registered."""
    mcp = FastMCP("test-arcane")
    containers.register(mcp)
    environments.register(mcp)
    images.register(mcp)
    networks.register(mcp)
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


def register_operations(mcp: FastMCP) -> FastMCP:
    """Register the safety/confirmation tools on an existing FastMCP instance."""
    from arcane_mcp.tools import operations

    operations.register(mcp)
    return mcp


def parse_multipart(request: Any) -> dict[str, str]:
    """Parse a ``multipart/form-data`` request into ``{part_name: text}``.

    Deliberately dependency-free: the tests only need plain text parts.
    """
    content_type = request.headers["content-type"]
    assert content_type.startswith("multipart/form-data"), content_type
    boundary = content_type.split("boundary=")[1].strip('"').encode()
    parts: dict[str, str] = {}
    for chunk in request.content.split(b"--" + boundary):
        if b"\r\n\r\n" not in chunk:
            continue
        head, body = chunk.split(b"\r\n\r\n", 1)
        if b'name="' not in head:
            continue
        name = head.split(b'name="', 1)[1].split(b'"', 1)[0].decode()
        if body.endswith(b"\r\n"):
            body = body[:-2]
        parts[name] = body.decode()
    return parts
