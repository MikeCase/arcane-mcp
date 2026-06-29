"""Tests for container tools."""
from __future__ import annotations

from typing import Any

import pytest

from tests.conftest import call_tool

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
    """inspect_container returns container details."""
    httpx_mock.add_response(
        url="http://localhost:3552/api/environments/0/containers/c1",
        method="GET",
        json={"id": "c1", "name": "web", "config": {}},
    )
    result = await call_tool(mcp, "inspect_container", container_id="c1")
    assert result["id"] == "c1"


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


# ── remove_container ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_remove_container_needs_confirm(mcp: Any, httpx_mock: Any) -> None:
    """remove_container returns warning when confirm=False."""
    result = await call_tool(mcp, "remove_container", container_id="c1")
    assert "warning" in result
    assert result["container_id"] == "c1"


@pytest.mark.asyncio
async def test_remove_container_confirmed(mcp: Any, httpx_mock: Any) -> None:
    """remove_container executes when confirm=True."""
    httpx_mock.add_response(
        url="http://localhost:3552/api/environments/0/containers/c1?force=false",
        method="DELETE",
        json={"message": "removed"},
    )
    result = await call_tool(mcp, "remove_container", container_id="c1", confirm=True)
    assert result == {"message": "removed"}


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
