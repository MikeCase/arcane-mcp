"""Tests for container tools."""

from __future__ import annotations

import json
from typing import Any

import pytest

from tests.conftest import call_tool, register_operations


@pytest.fixture
def ops_mcp(mcp: Any) -> Any:
    """MCP instance with the safety tools registered (for confirm_operation)."""
    return register_operations(mcp)


# ── list_containers ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_containers(mcp: Any, httpx_mock: Any) -> None:
    """List containers returns parsed JSON."""
    httpx_mock.add_response(
        url="http://localhost:3552/api/environments/0/containers?all=false",
        method="GET",
        json=[{"id": "c1", "name": "web", "status": "running"}],
    )
    result = await call_tool(mcp, "list_containers")
    assert result == [{"id": "c1", "name": "web", "status": "running"}]


@pytest.mark.asyncio
async def test_list_containers_all(mcp: Any, httpx_mock: Any) -> None:
    """list_containers passes the all flag."""
    httpx_mock.add_response(
        url="http://localhost:3552/api/environments/0/containers?all=true",
        method="GET",
        json=[],
    )
    result = await call_tool(mcp, "list_containers", all=True)
    assert result == []


@pytest.mark.asyncio
async def test_list_containers_http_error(mcp: Any, httpx_mock: Any) -> None:
    """list_containers returns error dict on HTTP error."""
    httpx_mock.add_response(status_code=500)
    result = await call_tool(mcp, "list_containers")
    assert "error" in result
    assert result["status_code"] == 500


# ── inspect_container ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_inspect_container(mcp: Any, httpx_mock: Any) -> None:
    """inspect_container wraps the details in a credential-sensitive envelope."""
    httpx_mock.add_response(
        url="http://localhost:3552/api/environments/0/containers/c1",
        method="GET",
        json={"id": "c1", "name": "web", "config": {}},
    )
    result = await call_tool(mcp, "inspect_container", container_id="c1")
    assert result["classification"] == "credential_sensitive"
    assert "warning" in result
    assert result["data"]["id"] == "c1"


# ── start / stop / restart ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_start_container(mcp: Any, httpx_mock: Any) -> None:
    """start_container posts to the start endpoint."""
    httpx_mock.add_response(
        url="http://localhost:3552/api/environments/0/containers/c1/start",
        method="POST",
        json={"message": "started"},
    )
    result = await call_tool(mcp, "start_container", container_id="c1")
    assert result == {"message": "started"}


@pytest.mark.asyncio
async def test_stop_container(mcp: Any, httpx_mock: Any) -> None:
    """stop_container posts with timeout."""
    httpx_mock.add_response(
        url="http://localhost:3552/api/environments/0/containers/c1/stop",
        method="POST",
        json={"message": "stopped"},
    )
    result = await call_tool(mcp, "stop_container", container_id="c1", timeout=30)
    assert result == {"message": "stopped"}
    assert json.loads(httpx_mock.get_requests()[0].content) == {"timeout": 30}


@pytest.mark.asyncio
async def test_restart_container(mcp: Any, httpx_mock: Any) -> None:
    """restart_container posts with timeout."""
    httpx_mock.add_response(
        url="http://localhost:3552/api/environments/0/containers/c1/restart",
        method="POST",
        json={"message": "restarted"},
    )
    result = await call_tool(mcp, "restart_container", container_id="c1")
    assert result == {"message": "restarted"}
    assert json.loads(httpx_mock.get_requests()[0].content) == {"timeout": 10}


# ── remove_container ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_remove_container_needs_confirm(mcp: Any, httpx_mock: Any) -> None:
    """remove_container returns a proposal and touches no endpoint."""
    result = await call_tool(mcp, "remove_container", container_id="c1")
    assert result["action"] == "remove_container"
    assert result["target"] == "c1"
    assert result["classification"] == "destructive_write"
    assert result["confirmation_token"]
    assert result["operation_hash"]
    assert "warning" in result
    assert httpx_mock.get_requests() == []


@pytest.mark.asyncio
async def test_remove_container_confirmed(ops_mcp: Any, httpx_mock: Any) -> None:
    """remove_container executes the DELETE after confirm_operation."""
    httpx_mock.add_response(
        url="http://localhost:3552/api/environments/0/containers/c1?force=false",
        method="DELETE",
        json={"message": "removed"},
    )
    proposal = await call_tool(ops_mcp, "remove_container", container_id="c1")
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
    assert request.url.path == "/api/environments/0/containers/c1"
    assert request.url.params["force"] == "false"
    assert request.content == b""


# ── create_container ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_container(mcp: Any, httpx_mock: Any) -> None:
    """create_container posts with image and name."""
    httpx_mock.add_response(
        url="http://localhost:3552/api/environments/0/containers",
        method="POST",
        json={"id": "new-container"},
    )
    result = await call_tool(mcp, "create_container", image="nginx", name="my-nginx")
    assert result == {"id": "new-container"}


# ── exec_in_container ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_exec_in_container(mcp: Any, httpx_mock: Any) -> None:
    """exec_in_container sends command payload."""
    httpx_mock.add_response(
        url="http://localhost:3552/api/environments/0/containers/c1/exec",
        method="POST",
        json={"output": "hello world"},
    )
    result = await call_tool(mcp, "exec_in_container", container_id="c1", command="echo hello")
    assert result == {"output": "hello world"}


# ── get_container_logs ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_container_logs(mcp: Any, httpx_mock: Any) -> None:
    """get_container_logs fetches logs with tail param."""
    httpx_mock.add_response(
        url="http://localhost:3552/api/environments/0/containers/c1/logs?tail=100",
        method="GET",
        json={"logs": "line1\nline2"},
    )
    result = await call_tool(mcp, "get_container_logs", container_id="c1")
    assert result == {"logs": "line1\nline2"}


# ── get_container_stats ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_container_stats(mcp: Any, httpx_mock: Any) -> None:
    """get_container_stats fetches resource stats."""
    httpx_mock.add_response(
        url="http://localhost:3552/api/environments/0/containers/c1/stats",
        method="GET",
        json={"cpu": 0.5, "memory": 1048576},
    )
    result = await call_tool(mcp, "get_container_stats", container_id="c1")
    assert result["cpu"] == 0.5
