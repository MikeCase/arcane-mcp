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
        url="http://localhost:3552/api/agents/0/containers?all=false",
        method="GET",
        json=[{"id": "c1", "name": "web", "status": "running"}],
    )
    result = await call_tool(mcp, "list_containers")
    assert result == [{"id": "c1", "name": "web", "status": "running"}]


@pytest.mark.asyncio
async def test_list_containers_all(mcp: Any, httpx_mock: Any) -> None:
    """list_containers passes the all flag."""
    httpx_mock.add_response(
        url="http://localhost:3552/api/agents/0/containers?all=true",
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
        url="http://localhost:3552/api/agents/0/containers/c1",
        method="GET",
        json={"id": "c1", "name": "web", "config": {}},
    )
    result = await call_tool(mcp, "inspect_container", container_id="c1")
    assert result["data"]["id"] == "c1"


# ── start / stop / restart ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_start_container(mcp: Any, httpx_mock: Any) -> None:
    """start_container posts to the start endpoint."""
    httpx_mock.add_response(
        url="http://localhost:3552/api/agents/0/containers/c1?action=start",
        method="POST",
        json={"message": "started"},
    )
    result = await call_tool(mcp, "start_container", container_id="c1")
    assert result == {"message": "started"}


@pytest.mark.asyncio
async def test_stop_container(mcp: Any, httpx_mock: Any) -> None:
    """stop_container posts with timeout."""
    httpx_mock.add_response(
        url="http://localhost:3552/api/agents/0/containers/c1?action=stop",
        method="POST",
        json={"message": "stopped"},
    )
    result = await call_tool(mcp, "stop_container", container_id="c1", timeout=30)
    assert result == {"message": "stopped"}


@pytest.mark.asyncio
async def test_restart_container(mcp: Any, httpx_mock: Any) -> None:
    """restart_container posts with timeout."""
    httpx_mock.add_response(
        url="http://localhost:3552/api/agents/0/containers/c1?action=restart",
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
    assert result["target"] == "c1"


@pytest.mark.asyncio
async def test_remove_container_confirmed(mcp: Any, httpx_mock: Any) -> None:
    """remove_container executes when confirm=True."""
    httpx_mock.add_response(
        url="http://localhost:3552/api/agents/0/containers/c1?force=false",
        method="DELETE",
        json={"message": "removed"},
    )
    proposal = await call_tool(mcp, "remove_container", container_id="c1")
    result = await call_tool(
        mcp, "confirm_operation",
        token=proposal["confirmation_token"], operation_hash=proposal["operation_hash"],
    )
    assert result == {"message": "removed"}


# ── create_container ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_container(mcp: Any, httpx_mock: Any) -> None:
    """create_container posts with image and name."""
    httpx_mock.add_response(
        url="http://localhost:3552/api/agents/0/containers",
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
        url="http://localhost:3552/api/agents/0/containers/c1/exec",
        method="POST",
        json={"output": "hello world"},
    )
    result = await call_tool(mcp, "exec_in_container", container_id="c1", command="echo hello")
    assert result == {"output": "hello world"}


# ── get_container_logs ────────────────────────────────────────────────


LOG_URL = "http://localhost:3552/api/agents/0/containers/c1/logs/download"
LOG_TEXT = "a info start\nb ERROR boom\nc info tick\nd error again\ne info tick\n"


@pytest.mark.asyncio
async def test_get_container_logs_tail(mcp: Any, httpx_mock: Any) -> None:
    """get_container_logs downloads the log and keeps the last `tail` lines."""
    httpx_mock.add_response(url=LOG_URL, method="GET", text=LOG_TEXT)
    result = await call_tool(mcp, "get_container_logs", container_id="c1", tail=2)
    assert result["logs"] == "d error again\ne info tick"
    assert result["matched_lines"] == 5
    assert result["returned_lines"] == 2


@pytest.mark.asyncio
async def test_get_container_logs_all(mcp: Any, httpx_mock: Any) -> None:
    """tail=0 returns every line."""
    httpx_mock.add_response(url=LOG_URL, method="GET", text=LOG_TEXT)
    result = await call_tool(mcp, "get_container_logs", container_id="c1", tail=0)
    assert result["returned_lines"] == 5


@pytest.mark.asyncio
async def test_get_container_logs_grep(mcp: Any, httpx_mock: Any) -> None:
    """grep filters case-insensitively before the tail is applied."""
    httpx_mock.add_response(url=LOG_URL, method="GET", text=LOG_TEXT)
    result = await call_tool(mcp, "get_container_logs", container_id="c1", tail=1, grep="error")
    assert result["logs"] == "d error again"
    assert result["matched_lines"] == 2


@pytest.mark.asyncio
async def test_get_container_logs_http_error(mcp: Any, httpx_mock: Any) -> None:
    """get_container_logs returns an error dict with the response body."""
    httpx_mock.add_response(url=LOG_URL, method="GET", status_code=403, text="forbidden")
    result = await call_tool(mcp, "get_container_logs", container_id="c1")
    assert result["status_code"] == 403
    assert result["detail"] == "forbidden"


# ── get_container_processes ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_container_processes(mcp: Any, httpx_mock: Any) -> None:
    """get_container_processes returns the process snapshot."""
    payload = {"success": True, "data": {"titles": ["PID", "%MEM"], "processes": [["1", "12.3"]]}}
    httpx_mock.add_response(
        url="http://localhost:3552/api/agents/0/containers/c1/processes",
        method="GET",
        json=payload,
    )
    result = await call_tool(mcp, "get_container_processes", container_id="c1")
    assert result == payload


# ── get_container_stats ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_container_stats_not_available(mcp: Any, httpx_mock: Any) -> None:
    """get_container_stats explains the API gap without calling Arcane."""
    result = await call_tool(mcp, "get_container_stats", container_id="c1")
    assert "WebSocket" in result["error"]
    assert httpx_mock.get_requests() == []
