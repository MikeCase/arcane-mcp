"""Tests for network tools."""
from __future__ import annotations

from typing import Any

import pytest

from tests.conftest import call_tool


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
    """remove_network returns warning when not confirmed."""
    result = await call_tool(mcp, "remove_network", network_id="net1")
    assert "warning" in result


@pytest.mark.asyncio
async def test_remove_network_confirmed(mcp: Any, httpx_mock: Any) -> None:
    """remove_network executes when confirmed."""
    httpx_mock.add_response(
        url="http://localhost:3552/api/environments/0/networks/net1",
        method="DELETE",
        json={"message": "removed"},
    )
    result = await call_tool(mcp, "remove_network", network_id="net1", confirm=True)
    assert result == {"message": "removed"}


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
