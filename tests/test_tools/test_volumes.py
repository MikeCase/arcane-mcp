"""Tests for volume tools."""

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
async def test_list_volumes(mcp: Any, httpx_mock: Any) -> None:
    """list_volumes returns volumes list."""
    httpx_mock.add_response(
        url="http://localhost:3552/api/environments/0/volumes",
        method="GET",
        json=[{"name": "data-vol", "driver": "local"}],
    )
    result = await call_tool(mcp, "list_volumes")
    assert result == [{"name": "data-vol", "driver": "local"}]


@pytest.mark.asyncio
async def test_create_volume(mcp: Any, httpx_mock: Any) -> None:
    """create_volume posts with name and driver."""
    httpx_mock.add_response(
        url="http://localhost:3552/api/environments/0/volumes",
        method="POST",
        json={"name": "my-vol", "driver": "local"},
    )
    result = await call_tool(mcp, "create_volume", name="my-vol")
    assert result["name"] == "my-vol"


@pytest.mark.asyncio
async def test_inspect_volume(mcp: Any, httpx_mock: Any) -> None:
    """inspect_volume returns volume details."""
    httpx_mock.add_response(
        url="http://localhost:3552/api/environments/0/volumes/my-vol",
        method="GET",
        json={"name": "my-vol", "mountpoint": "/data"},
    )
    result = await call_tool(mcp, "inspect_volume", name="my-vol")
    assert result["mountpoint"] == "/data"


@pytest.mark.asyncio
async def test_remove_volume_needs_confirm(mcp: Any, httpx_mock: Any) -> None:
    """remove_volume returns a proposal and touches no endpoint."""
    result = await call_tool(mcp, "remove_volume", name="my-vol")
    assert result["action"] == "remove_volume"
    assert result["target"] == "volume:my-vol"
    assert result["classification"] == "destructive_write"
    assert result["confirmation_token"]
    assert result["operation_hash"]
    assert "warning" in result
    assert httpx_mock.get_requests() == []


@pytest.mark.asyncio
async def test_remove_volume_confirmed(ops_mcp: Any, httpx_mock: Any) -> None:
    """remove_volume executes the DELETE after confirm_operation."""
    httpx_mock.add_response(
        url="http://localhost:3552/api/environments/0/volumes/my-vol",
        method="DELETE",
        json={"message": "removed"},
    )
    proposal = await call_tool(ops_mcp, "remove_volume", name="my-vol")
    assert httpx_mock.get_requests() == []

    result = await call_tool(
        ops_mcp,
        "confirm_operation",
        token=proposal["confirmation_token"],
        operation_hash=proposal["operation_hash"],
    )
    assert result == {"message": "removed"}

    request = httpx_mock.get_requests()[0]
    assert request.method == "DELETE"
    assert request.url.path == "/api/environments/0/volumes/my-vol"
    assert json.loads(request.content) == {"force": "false"}
