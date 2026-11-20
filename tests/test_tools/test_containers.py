"""Tests for container tools.

Routes target Arcane v3 only: ``/api/agents/{env_id}/...`` with lifecycle
actions carried on the ``action`` query parameter (``POST /containers/{id}
?action=start``) and list endpoints going through ``paginate_all``.
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


# ── list_containers ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_containers(mcp: Any, httpx_mock: Any) -> None:
    """list_containers returns the merged paginated envelope."""
    httpx_mock.add_response(
        method="GET",
        json={"data": [{"id": "c1", "name": "web", "status": "running"}], "pagination": {"hasNextPage": False}},
    )
    result = await call_tool(mcp, "list_containers")
    assert result["data"] == [{"id": "c1", "name": "web", "status": "running"}]

    request = httpx_mock.get_requests()[0]
    assert request.url.path == "/api/agents/0/containers"
    assert request.url.params["all"] == "false"
    assert request.url.params["start"] == "0"
    assert request.url.params["limit"] == "100"


@pytest.mark.asyncio
async def test_list_containers_all(mcp: Any, httpx_mock: Any) -> None:
    """list_containers passes the all flag."""
    httpx_mock.add_response(method="GET", json={"data": [], "pagination": {"hasNextPage": False}})
    result = await call_tool(mcp, "list_containers", all=True)
    assert result["data"] == []
    assert httpx_mock.get_requests()[0].url.params["all"] == "true"


@pytest.mark.asyncio
async def test_list_containers_walks_pages(mcp: Any, httpx_mock: Any) -> None:
    """list_containers follows pagination.hasNextPage instead of stopping at 20."""
    httpx_mock.add_response(method="GET", json={"data": [{"id": "c1"}], "pagination": {"hasNextPage": True}})
    httpx_mock.add_response(method="GET", json={"data": [{"id": "c2"}], "pagination": {"hasNextPage": False}})

    result = await call_tool(mcp, "list_containers")
    assert [c["id"] for c in result["data"]] == ["c1", "c2"]
    assert result["pagination"]["totalItems"] == 2

    requests = httpx_mock.get_requests()
    assert [r.url.params["start"] for r in requests] == ["0", "1"]


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
        url="http://localhost:3552/api/agents/0/containers/c1",
        method="GET",
        json={"id": "c1", "name": "web", "config": {}},
    )
    result = await call_tool(mcp, "inspect_container", container_id="c1")
    assert result["classification"] == "credential_sensitive"
    assert "warning" in result
    assert result["data"]["id"] == "c1"


# ── start / stop / restart / pause / unpause ──────────────────────────


@pytest.mark.asyncio
async def test_start_container(mcp: Any, httpx_mock: Any) -> None:
    """start_container posts the action query param, with no body."""
    httpx_mock.add_response(method="POST", json={"message": "started"})
    result = await call_tool(mcp, "start_container", container_id="c1")
    assert result == {"message": "started"}

    request = httpx_mock.get_requests()[0]
    assert request.method == "POST"
    assert request.url.path == "/api/agents/0/containers/c1"
    assert request.url.params["action"] == "start"
    assert request.content == b""


@pytest.mark.asyncio
async def test_stop_container(mcp: Any, httpx_mock: Any) -> None:
    """stop_container posts action=stop and sends no body (v3 has no timeout)."""
    httpx_mock.add_response(method="POST", json={"message": "stopped"})
    result = await call_tool(mcp, "stop_container", container_id="c1", timeout=30)
    assert result == {"message": "stopped"}

    request = httpx_mock.get_requests()[0]
    assert request.url.path == "/api/agents/0/containers/c1"
    assert request.url.params["action"] == "stop"
    assert request.content == b""


@pytest.mark.asyncio
async def test_restart_container(mcp: Any, httpx_mock: Any) -> None:
    """restart_container posts action=restart and sends no body."""
    httpx_mock.add_response(method="POST", json={"message": "restarted"})
    result = await call_tool(mcp, "restart_container", container_id="c1")
    assert result == {"message": "restarted"}

    request = httpx_mock.get_requests()[0]
    assert request.url.path == "/api/agents/0/containers/c1"
    assert request.url.params["action"] == "restart"
    assert request.content == b""


@pytest.mark.asyncio
async def test_pause_container(mcp: Any, httpx_mock: Any) -> None:
    """pause_container posts action=pause."""
    httpx_mock.add_response(method="POST", json={"message": "paused"})
    result = await call_tool(mcp, "pause_container", container_id="c1")
    assert result == {"message": "paused"}
    assert httpx_mock.get_requests()[0].url.params["action"] == "pause"


@pytest.mark.asyncio
async def test_unpause_container(mcp: Any, httpx_mock: Any) -> None:
    """unpause_container posts action=unpause."""
    httpx_mock.add_response(method="POST", json={"message": "unpaused"})
    result = await call_tool(mcp, "unpause_container", container_id="c1")
    assert result == {"message": "unpaused"}
    assert httpx_mock.get_requests()[0].url.params["action"] == "unpause"


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
    httpx_mock.add_response(method="DELETE", json={"message": "removed"})
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
    assert request.url.path == "/api/agents/0/containers/c1"
    assert request.url.params["force"] == "false"
    assert request.content == b""


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
async def test_exec_in_container_reports_unavailable(mcp: Any, httpx_mock: Any) -> None:
    """exec_in_container explains the API gap without issuing a request."""
    result = await call_tool(mcp, "exec_in_container", container_id="c1", command="echo hello")
    assert "does not expose a container exec endpoint" in result["error"]
    assert result["container_id"] == "c1"
    assert httpx_mock.get_requests() == []


# ── get_container_logs ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_container_logs_reports_unavailable(mcp: Any, httpx_mock: Any) -> None:
    """get_container_logs explains the API gap without issuing a request."""
    result = await call_tool(mcp, "get_container_logs", container_id="c1")
    assert "Use SSH" in result["error"]
    assert result["container_id"] == "c1"
    assert httpx_mock.get_requests() == []


# ── get_container_stats ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_container_stats_reports_unavailable(mcp: Any, httpx_mock: Any) -> None:
    """get_container_stats explains the API gap without issuing a request."""
    result = await call_tool(mcp, "get_container_stats", container_id="c1")
    assert "Stats endpoint not available" in result["error"]
    assert result["container_id"] == "c1"
    assert httpx_mock.get_requests() == []


# ── kill_container ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_kill_container_needs_confirm(mcp: Any, httpx_mock: Any) -> None:
    """kill_container returns a proposal and touches no endpoint."""
    result = await call_tool(mcp, "kill_container", container_id="c1")
    assert result["action"] == "kill_container"
    assert result["confirmation_token"]
    assert httpx_mock.get_requests() == []


@pytest.mark.asyncio
async def test_kill_container_confirmed(ops_mcp: Any, httpx_mock: Any) -> None:
    """kill_container executes POST /containers/{id}?action=kill after confirm."""
    httpx_mock.add_response(method="POST", json={"message": "killed"})
    proposal = await call_tool(ops_mcp, "kill_container", container_id="c1")
    assert httpx_mock.get_requests() == []

    result = await call_tool(
        ops_mcp,
        "confirm_operation",
        token=proposal["confirmation_token"],
        operation_hash=proposal["operation_hash"],
    )
    assert result == {"message": "killed"}

    request = httpx_mock.get_requests()[0]
    assert request.method == "POST"
    assert request.url.path == "/api/agents/0/containers/c1"
    assert request.url.params["action"] == "kill"
    assert "signal" not in request.url.params
    assert request.content == b""


@pytest.mark.asyncio
async def test_kill_container_confirmed_with_signal(ops_mcp: Any, httpx_mock: Any) -> None:
    """kill_container forwards the signal query param through confirmation."""
    httpx_mock.add_response(method="POST", json={"message": "killed"})
    proposal = await call_tool(ops_mcp, "kill_container", container_id="c1", signal="SIGTERM")

    await call_tool(
        ops_mcp,
        "confirm_operation",
        token=proposal["confirmation_token"],
        operation_hash=proposal["operation_hash"],
    )

    params = httpx_mock.get_requests()[0].url.params
    assert params["action"] == "kill"
    assert params["signal"] == "SIGTERM"


# ── set_container_auto_update ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_set_container_auto_update(mcp: Any, httpx_mock: Any) -> None:
    """set_container_auto_update PUTs to the v3 autoupdate path."""
    httpx_mock.add_response(method="PUT", json={"message": "updated"})
    result = await call_tool(mcp, "set_container_auto_update", container_id="c1", enabled=True)
    assert result == {"message": "updated"}

    request = httpx_mock.get_requests()[0]
    assert request.method == "PUT"
    assert request.url.path == "/api/agents/0/containers/c1/autoupdate"
    assert json.loads(request.content) == {"enabled": True}


# ── counts / redeploy / commit / update ───────────────────────────────


@pytest.mark.asyncio
async def test_get_container_counts(mcp: Any, httpx_mock: Any) -> None:
    """get_container_counts hits the counts route."""
    httpx_mock.add_response(
        url="http://localhost:3552/api/agents/0/containers/counts",
        method="GET",
        json={"running": 2, "stopped": 1},
    )
    result = await call_tool(mcp, "get_container_counts")
    assert result == {"running": 2, "stopped": 1}
