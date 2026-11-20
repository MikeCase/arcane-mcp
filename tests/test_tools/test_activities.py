"""Tests for activity and event tools."""

from __future__ import annotations

from typing import Any

import pytest
from fastmcp import FastMCP

from arcane_mcp.tools import activities
from tests.conftest import call_tool, register_operations


@pytest.fixture
def mcp() -> FastMCP:
    """Return an MCP instance with the activities/events tools registered."""
    mcp = FastMCP("test-arcane")
    activities.register(mcp)
    return mcp


@pytest.fixture
def ops_mcp(mcp: FastMCP) -> FastMCP:
    """MCP instance with the safety tools registered (for confirm_operation)."""
    return register_operations(mcp)


def _page(data: list[dict[str, Any]], has_next: bool = False) -> dict[str, Any]:
    """Build a v3 paginated envelope."""
    return {
        "data": data,
        "pagination": {"hasNextPage": has_next, "currentPage": 1, "itemsPerPage": len(data)},
        "success": True,
    }


# ── activities ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_activities_paginates(mcp: Any, httpx_mock: Any) -> None:
    """list_activities walks every page of the v3 collection."""
    httpx_mock.add_response(
        url="http://localhost:3552/api/agents/0/activities",
        method="GET",
        match_params={"start": "0", "limit": "100"},
        json=_page([{"id": "act1"}], has_next=True),
    )
    httpx_mock.add_response(
        url="http://localhost:3552/api/agents/0/activities",
        method="GET",
        match_params={"start": "1", "limit": "100"},
        json=_page([{"id": "act2"}]),
    )

    result = await call_tool(mcp, "list_activities")

    assert [activity["id"] for activity in result["data"]] == ["act1", "act2"]
    assert len(httpx_mock.get_requests()) == 2


@pytest.mark.asyncio
async def test_get_activity(mcp: Any, httpx_mock: Any) -> None:
    """get_activity reads a single activity by id."""
    httpx_mock.add_response(
        url="http://localhost:3552/api/agents/0/activities/act1",
        method="GET",
        json={"id": "act1", "status": "running"},
    )
    result = await call_tool(mcp, "get_activity", activity_id="act1")
    assert result["status"] == "running"


@pytest.mark.asyncio
async def test_cancel_activity_uses_query_param(mcp: Any, httpx_mock: Any) -> None:
    """cancel_activity is POST /activities/{id}?action=cancel (no /cancel sub-path)."""
    httpx_mock.add_response(
        url="http://localhost:3552/api/agents/0/activities/act1",
        method="POST",
        match_params={"action": "cancel"},
        json={"success": True},
    )
    result = await call_tool(mcp, "cancel_activity", activity_id="act1")
    assert result == {"success": True}

    request = httpx_mock.get_requests()[0]
    assert request.method == "POST"
    assert request.url.path == "/api/agents/0/activities/act1"
    assert request.url.params["action"] == "cancel"


@pytest.mark.asyncio
async def test_clear_activity_history_needs_confirm(mcp: Any, httpx_mock: Any) -> None:
    """clear_activity_history is destructive: propose first, execute on confirm."""
    proposal = await call_tool(mcp, "clear_activity_history", dry_run=False)
    assert proposal["confirmation_token"]
    assert httpx_mock.get_requests() == []

    httpx_mock.add_response(
        url="http://localhost:3552/api/agents/0/activities/history",
        method="DELETE",
        json={"success": True},
    )
    ops = register_operations(mcp)
    result = await call_tool(
        ops,
        "confirm_operation",
        token=proposal["confirmation_token"],
        operation_hash=proposal["operation_hash"],
    )
    assert result == {"success": True}
    assert httpx_mock.get_requests()[0].method == "DELETE"


# ── events ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_events_paginates(mcp: Any, httpx_mock: Any) -> None:
    """list_events reads the global /api/events collection, page by page."""
    httpx_mock.add_response(
        url="http://localhost:3552/api/events",
        method="GET",
        match_params={"start": "0", "limit": "100"},
        json=_page([{"id": "ev1"}], has_next=True),
    )
    httpx_mock.add_response(
        url="http://localhost:3552/api/events",
        method="GET",
        match_params={"start": "1", "limit": "100"},
        json=_page([{"id": "ev2"}]),
    )

    result = await call_tool(mcp, "list_events")

    assert [event["id"] for event in result["data"]] == ["ev1", "ev2"]


@pytest.mark.asyncio
async def test_get_environment_events_uses_agent_route(mcp: Any, httpx_mock: Any) -> None:
    """v3 renamed /events/environment/{id} to /events/agent/{id}."""
    httpx_mock.add_response(
        url="http://localhost:3552/api/events/agent/env-42",
        method="GET",
        match_params={"start": "0", "limit": "100"},
        json=_page([{"id": "ev1"}]),
    )
    result = await call_tool(mcp, "get_environment_events", environment_id="env-42")

    assert [event["id"] for event in result["data"]] == ["ev1"]
    assert httpx_mock.get_requests()[0].url.path == "/api/events/agent/env-42"


@pytest.mark.asyncio
async def test_delete_event_needs_confirm(ops_mcp: Any, httpx_mock: Any) -> None:
    """delete_event proposes DELETE /api/events/{id} and runs it on confirm."""
    proposal = await call_tool(ops_mcp, "delete_event", event_id="ev1")
    assert proposal["classification"] == "destructive_write"
    assert httpx_mock.get_requests() == []

    httpx_mock.add_response(
        url="http://localhost:3552/api/events/ev1",
        method="DELETE",
        json={"success": True},
    )
    result = await call_tool(
        ops_mcp,
        "confirm_operation",
        token=proposal["confirmation_token"],
        operation_hash=proposal["operation_hash"],
    )
    assert result == {"success": True}
    assert httpx_mock.get_requests()[0].url.path == "/api/events/ev1"
