"""Tests for network tools."""

from __future__ import annotations

from typing import Any

import pytest

from tests.conftest import call_tool, register_operations


@pytest.fixture
def ops_mcp(mcp: Any) -> Any:
    """MCP instance with the safety tools registered (for confirm_operation)."""
    return register_operations(mcp)


@pytest.mark.asyncio
async def test_list_networks(mcp: Any, httpx_mock: Any) -> None:
    """list_networks returns networks list."""
    httpx_mock.add_response(
        url="http://localhost:3552/api/environments/0/networks",
        method="GET",
        json=[{"id": "net1", "name": "bridge"}],
    )
    result = await call_tool(mcp, "list_networks")
    assert result == [{"id": "net1", "name": "bridge"}]


@pytest.mark.asyncio
async def test_create_network(mcp: Any, httpx_mock: Any) -> None:
    """create_network posts with name and driver."""
    httpx_mock.add_response(
        url="http://localhost:3552/api/environments/0/networks",
        method="POST",
        json={"id": "net2", "name": "my-net"},
    )
    result = await call_tool(mcp, "create_network", name="my-net", driver="overlay")
    assert result["name"] == "my-net"


@pytest.mark.asyncio
async def test_inspect_network(mcp: Any, httpx_mock: Any) -> None:
    """inspect_network returns network details."""
    httpx_mock.add_response(
        url="http://localhost:3552/api/environments/0/networks/net1",
        method="GET",
        json={"id": "net1", "name": "bridge"},
    )
    result = await call_tool(mcp, "inspect_network", network_id="net1")
    assert result["id"] == "net1"


@pytest.mark.asyncio
async def test_remove_network_needs_confirm(mcp: Any, httpx_mock: Any) -> None:
    """remove_network returns a proposal and touches no endpoint."""
    result = await call_tool(mcp, "remove_network", network_id="net1")
    assert result["action"] == "remove_network"
    assert result["target"] == "network:net1"
    assert result["classification"] == "destructive_write"
    assert result["confirmation_token"]
    assert result["operation_hash"]
    assert "warning" in result
    assert httpx_mock.get_requests() == []


@pytest.mark.asyncio
async def test_remove_network_confirmed(ops_mcp: Any, httpx_mock: Any) -> None:
    """remove_network executes the DELETE after confirm_operation."""
    httpx_mock.add_response(
        url="http://localhost:3552/api/environments/0/networks/net1",
        method="DELETE",
        json={"message": "removed"},
    )
    proposal = await call_tool(ops_mcp, "remove_network", network_id="net1")
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
    assert request.url.path == "/api/environments/0/networks/net1"
    assert request.content == b""


@pytest.mark.asyncio
async def test_connect_container(mcp: Any, httpx_mock: Any) -> None:
    """connect_container_to_network connects a container."""
    httpx_mock.add_response(
        url="http://localhost:3552/api/environments/0/networks/net1/connect",
        method="POST",
        json={"message": "connected"},
    )
    result = await call_tool(mcp, "connect_container_to_network", network_id="net1", container_id="c1")
    assert result == {"message": "connected"}


@pytest.mark.asyncio
async def test_disconnect_container(mcp: Any, httpx_mock: Any) -> None:
    """disconnect_container_from_network disconnects a container."""
    httpx_mock.add_response(
        url="http://localhost:3552/api/environments/0/networks/net1/disconnect",
        method="POST",
        json={"message": "disconnected"},
    )
    result = await call_tool(mcp, "disconnect_container_from_network", network_id="net1", container_id="c1")
    assert result == {"message": "disconnected"}
