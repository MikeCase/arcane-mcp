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
        url="http://localhost:3552/api/agents/0/system/docker/info",
        method="GET",
        json={"containers": 5, "images": 10},
    )
    result = await call_tool(mcp, "get_docker_info")
    assert result["containers"] == 5


@pytest.mark.asyncio
async def test_get_docker_version(mcp: Any, httpx_mock: Any) -> None:
    """get_docker_version returns version info."""
    httpx_mock.add_response(
        url="http://localhost:3552/api/agents/0/version",
        method="GET",
        json={"version": "24.0.7"},
    )
    result = await call_tool(mcp, "get_docker_version")
    assert result["version"] == "24.0.7"


# ── health (HEAD only in v3) ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_system_health_uses_head(mcp: Any, httpx_mock: Any) -> None:
    """v3 serves HEAD /system/health only; the status code is the whole answer."""
    httpx_mock.add_response(
        url="http://localhost:3552/api/agents/0/system/health",
        method="HEAD",
        status_code=200,
        headers={"X-Request-Id": "req-1"},
    )
    result = await call_tool(mcp, "get_system_health")

    assert result["status"] == 200
    assert result["healthy"] is True
    assert result["headers"]["x-request-id"] == "req-1"

    request = httpx_mock.get_requests()[0]
    assert request.method == "HEAD"
    assert request.url.path == "/api/agents/0/system/health"


@pytest.mark.asyncio
async def test_get_system_health_reports_unhealthy_status(mcp: Any, httpx_mock: Any) -> None:
    """A 5xx from HEAD is an unhealthy result, not an error envelope."""
    httpx_mock.add_response(
        url="http://localhost:3552/api/agents/0/system/health",
        method="HEAD",
        status_code=503,
    )
    result = await call_tool(mcp, "get_system_health")

    assert result["status"] == 503
    assert result["healthy"] is False
    assert "error" not in result


# ── prune ──────────────────────────────────────────────────────────────


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
        url="http://localhost:3552/api/agents/0/system/prune",
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
    assert request.url.path == "/api/agents/0/system/prune"
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
        url="http://localhost:3552/api/agents/0/system/prune",
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


# ── upgrade ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_check_system_upgrade(mcp: Any, httpx_mock: Any) -> None:
    """check_system_upgrade reads /system/upgrade/check."""
    httpx_mock.add_response(
        url="http://localhost:3552/api/agents/0/system/upgrade/check",
        method="GET",
        json={"message": "System can be upgraded", "canUpgrade": True, "error": False},
    )
    result = await call_tool(mcp, "check_system_upgrade")
    assert result["canUpgrade"] is True


@pytest.mark.asyncio
async def test_trigger_upgrade_proposes_job(ops_mcp: Any, httpx_mock: Any) -> None:
    """trigger_upgrade proposes POST /system/upgrade/jobs with the target env."""
    proposal = await call_tool(ops_mcp, "trigger_upgrade")
    assert proposal["action"] == "trigger_upgrade"
    assert proposal["classification"] == "destructive_write"
    assert httpx_mock.get_requests() == []

    httpx_mock.add_response(
        url="http://localhost:3552/api/agents/0/system/upgrade/jobs",
        method="POST",
        status_code=202,
        json={"data": {"id": "job-1", "status": "pending"}, "success": True},
    )
    result = await call_tool(
        ops_mcp,
        "confirm_operation",
        token=proposal["confirmation_token"],
        operation_hash=proposal["operation_hash"],
    )
    assert result["data"]["id"] == "job-1"

    request = httpx_mock.get_requests()[0]
    assert request.method == "POST"
    assert request.url.path == "/api/agents/0/system/upgrade/jobs"
    # The job system is JSON, not a streamed action log.
    assert request.headers["content-type"] == "application/json"
    assert json.loads(request.content) == {"environmentIds": ["0"]}


# ── bulk container actions ─────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("tool_name", "action"),
    [
        ("start_all_containers", "startall"),
        ("start_stopped_containers", "startstopped"),
        ("stop_all_containers", "stopall"),
    ],
)
async def test_bulk_container_action_uses_query_param(ops_mcp: Any, httpx_mock: Any, tool_name: str, action: str) -> None:
    """Bulk container actions are POST /system/containers?action=<lowercase>."""
    proposal = await call_tool(ops_mcp, tool_name)
    assert proposal["action"] == tool_name
    assert httpx_mock.get_requests() == []

    httpx_mock.add_response(
        url="http://localhost:3552/api/agents/0/system/containers",
        method="POST",
        match_params={"action": action},
        json={"success": True},
    )
    result = await call_tool(
        ops_mcp,
        "confirm_operation",
        token=proposal["confirmation_token"],
        operation_hash=proposal["operation_hash"],
    )
    assert result == {"success": True}

    request = httpx_mock.get_requests()[0]
    assert request.method == "POST"
    assert request.url.path == "/api/agents/0/system/containers"
    assert request.url.params["action"] == action
    # No body: the action travels in the query string.
    assert request.content == b""
