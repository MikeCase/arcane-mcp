"""Tests for network tools.

Routes target Arcane v3 only: ``/api/agents/{env_id}/...`` with connect /
disconnect carried on the ``action`` query parameter and a
``NetworkContainerRequest`` JSON body, and list endpoints going through
``paginate_all``.
"""

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
async def test_list_networks(mcp: Any, httpx_mock: Any) -> None:
    """list_networks returns the merged paginated envelope."""
    httpx_mock.add_response(
        method="GET",
        json={"data": [{"id": "net1", "name": "bridge"}], "pagination": {"hasNextPage": False}},
    )
    result = await call_tool(mcp, "list_networks")
    assert result["data"] == [{"id": "net1", "name": "bridge"}]

    request = httpx_mock.get_requests()[0]
    assert request.url.path == "/api/agents/0/networks"
    assert request.url.params["start"] == "0"
    assert request.url.params["limit"] == "100"


@pytest.mark.asyncio
async def test_list_networks_walks_pages(mcp: Any, httpx_mock: Any) -> None:
    """list_networks follows pagination.hasNextPage instead of stopping at 20."""
    httpx_mock.add_response(method="GET", json={"data": [{"id": "net1"}], "pagination": {"hasNextPage": True}})
    httpx_mock.add_response(method="GET", json={"data": [{"id": "net2"}], "pagination": {"hasNextPage": False}})

    result = await call_tool(mcp, "list_networks")
    assert [n["id"] for n in result["data"]] == ["net1", "net2"]
    assert [r.url.params["start"] for r in httpx_mock.get_requests()] == ["0", "1"]


@pytest.mark.asyncio
async def test_list_networks_http_error(mcp: Any, httpx_mock: Any) -> None:
    """list_networks returns an error dict on HTTP error."""
    httpx_mock.add_response(status_code=500)
    result = await call_tool(mcp, "list_networks")
    assert "error" in result
    assert result["status_code"] == 500


@pytest.mark.asyncio
async def test_create_network(mcp: Any, httpx_mock: Any) -> None:
    """create_network posts with name and driver."""
    httpx_mock.add_response(
        url="http://localhost:3552/api/agents/0/networks",
        method="POST",
        json={"id": "net2", "name": "my-net"},
    )
    result = await call_tool(mcp, "create_network", name="my-net", driver="overlay")
    assert result["name"] == "my-net"


@pytest.mark.asyncio
async def test_inspect_network(mcp: Any, httpx_mock: Any) -> None:
    """inspect_network returns network details."""
    httpx_mock.add_response(
        url="http://localhost:3552/api/agents/0/networks/net1",
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
    httpx_mock.add_response(method="DELETE", json={"message": "removed"})
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
    assert request.url.path == "/api/agents/0/networks/net1"
    assert request.content == b""


@pytest.mark.asyncio
async def test_connect_container(mcp: Any, httpx_mock: Any) -> None:
    """connect_container_to_network posts action=connect with a containerId body."""
    httpx_mock.add_response(method="POST", json={"message": "connected"})
    result = await call_tool(mcp, "connect_container_to_network", network_id="net1", container_id="c1")
    assert result == {"message": "connected"}

    request = httpx_mock.get_requests()[0]
    assert request.method == "POST"
    assert request.url.path == "/api/agents/0/networks/net1"
    assert request.url.params["action"] == "connect"
    assert json.loads(request.content) == {"containerId": "c1"}


@pytest.mark.asyncio
async def test_disconnect_container(mcp: Any, httpx_mock: Any) -> None:
    """disconnect_container_from_network posts action=disconnect with force=false."""
    httpx_mock.add_response(method="POST", json={"message": "disconnected"})
    result = await call_tool(mcp, "disconnect_container_from_network", network_id="net1", container_id="c1")
    assert result == {"message": "disconnected"}

    request = httpx_mock.get_requests()[0]
    assert request.method == "POST"
    assert request.url.path == "/api/agents/0/networks/net1"
    assert request.url.params["action"] == "disconnect"
    assert json.loads(request.content) == {"containerId": "c1", "force": False}


@pytest.mark.asyncio
async def test_prune_networks_dry_run(mcp: Any, httpx_mock: Any) -> None:
    """prune_networks defaults to a dry run and touches no endpoint."""
    result = await call_tool(mcp, "prune_networks")
    assert result["dry_run"] is True
    assert httpx_mock.get_requests() == []


@pytest.mark.asyncio
async def test_get_network_counts(mcp: Any, httpx_mock: Any) -> None:
    """get_network_counts hits the counts route."""
    httpx_mock.add_response(
        url="http://localhost:3552/api/agents/0/networks/counts",
        method="GET",
        json={"total": 3},
    )
    result = await call_tool(mcp, "get_network_counts")
    assert result == {"total": 3}


@pytest.mark.asyncio
async def test_get_network_topology(mcp: Any, httpx_mock: Any) -> None:
    """get_network_topology hits the topology route."""
    httpx_mock.add_response(
        url="http://localhost:3552/api/agents/0/networks/topology",
        method="GET",
        json={"nodes": []},
    )
    result = await call_tool(mcp, "get_network_topology")
    assert result == {"nodes": []}
