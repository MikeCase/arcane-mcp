"""Tests for system tools."""

from __future__ import annotations

import json
from typing import Any

import pytest

from tests.conftest import call_tool, register_operations


@pytest.fixture
def ops_mcp(mcp: Any) -> Any:
    """MCP instance with the safety tools registered (for confirm_operation)."""
    return register_operations(mcp)


@pytest.mark.asyncio
async def test_get_docker_info(mcp: Any, httpx_mock: Any) -> None:
    """get_docker_info reads the /system/docker/info endpoint."""
    httpx_mock.add_response(
        url="http://localhost:3552/api/environments/0/system/docker/info",
        method="GET",
        json={"containers": 5, "images": 10},
    )
    result = await call_tool(mcp, "get_docker_info")
    assert result["containers"] == 5


@pytest.mark.asyncio
async def test_get_docker_version(mcp: Any, httpx_mock: Any) -> None:
    """get_docker_version returns version info."""
    httpx_mock.add_response(
        url="http://localhost:3552/api/environments/0/version",
        method="GET",
        json={"version": "24.0.7"},
    )
    result = await call_tool(mcp, "get_docker_version")
    assert result["version"] == "24.0.7"


@pytest.mark.asyncio
async def test_prune_system_dry_run_by_default(mcp: Any, httpx_mock: Any) -> None:
    """prune_system default is a dry run: no token and no request."""
    result = await call_tool(mcp, "prune_system")
    assert result["dry_run"] is True
    assert result["action"] == "prune_system"
    assert "confirmation_token" not in result
    assert httpx_mock.get_requests() == []


@pytest.mark.asyncio
async def test_prune_system_needs_confirm(mcp: Any, httpx_mock: Any) -> None:
    """prune_system(dry_run=False) returns a proposal and touches no endpoint."""
    result = await call_tool(mcp, "prune_system", dry_run=False)
    assert result["action"] == "prune_system"
    assert result["target"] == "system:0"
    assert result["classification"] == "destructive_write"
    assert result["confirmation_token"]
    assert result["operation_hash"]
    assert "warning" in result
    assert httpx_mock.get_requests() == []


@pytest.mark.asyncio
async def test_prune_system_confirmed(ops_mcp: Any, httpx_mock: Any) -> None:
    """prune_system executes the POST after confirm_operation."""
    httpx_mock.add_response(
        url="http://localhost:3552/api/environments/0/system/prune",
        method="POST",
        json={"reclaimed": "100MB"},
    )
    proposal = await call_tool(ops_mcp, "prune_system", dry_run=False)
    assert httpx_mock.get_requests() == []

    result = await call_tool(
        ops_mcp,
        "confirm_operation",
        token=proposal["confirmation_token"],
        operation_hash=proposal["operation_hash"],
    )
    assert result == {"reclaimed": "100MB"}

    request = httpx_mock.get_requests()[0]
    assert request.method == "POST"
    assert request.url.path == "/api/environments/0/system/prune"
    assert json.loads(request.content) == {
        "containers": True,
        "images": True,
        "volumes": False,
        "networks": True,
        "buildCache": False,
    }


@pytest.mark.asyncio
async def test_prune_system_with_volumes(ops_mcp: Any, httpx_mock: Any) -> None:
    """prune_system sends the volumes flag in the confirmed body."""
    httpx_mock.add_response(
        url="http://localhost:3552/api/environments/0/system/prune",
        method="POST",
        json={"reclaimed": "200MB"},
    )
    proposal = await call_tool(ops_mcp, "prune_system", dry_run=False, volumes=True)

    result = await call_tool(
        ops_mcp,
        "confirm_operation",
        token=proposal["confirmation_token"],
        operation_hash=proposal["operation_hash"],
    )
    assert result == {"reclaimed": "200MB"}

    body = json.loads(httpx_mock.get_requests()[0].content)
    assert body["volumes"] is True
