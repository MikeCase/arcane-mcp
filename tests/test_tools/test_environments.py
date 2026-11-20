"""Tests for environment (agent) tools against the Arcane v3 routes."""

from __future__ import annotations

import json
from typing import Any

import pytest

from tests.conftest import call_tool, register_operations

BASE = "http://localhost:3552/api/agents"


@pytest.fixture
def ops_mcp(mcp: Any) -> Any:
    """MCP instance with the safety tools registered (for confirm_operation)."""
    return register_operations(mcp)


@pytest.mark.asyncio
async def test_list_environments(mcp: Any, httpx_mock: Any) -> None:
    """list_environments reads the paginated agent collection."""
    httpx_mock.add_response(
        url=BASE,
        method="GET",
        match_params={"start": "0", "limit": "100"},
        json={
            "data": [{"id": "0", "name": "local"}, {"id": "uuid-1", "name": "remote"}],
            "pagination": {"hasNextPage": False, "totalItems": 2},
            "success": True,
        },
    )
    result = await call_tool(mcp, "list_environments")
    assert len(result["data"]) == 2

    request = httpx_mock.get_requests()[0]
    assert request.url.path == "/api/agents"
    assert request.url.params["start"] == "0"
    assert request.url.params["limit"] == "100"


@pytest.mark.asyncio
async def test_list_environments_follows_pages(mcp: Any, httpx_mock: Any) -> None:
    """list_environments keeps paging while hasNextPage is true."""
    httpx_mock.add_response(
        url=BASE,
        method="GET",
        match_params={"start": "0", "limit": "100"},
        json={"data": [{"id": "0"}], "pagination": {"hasNextPage": True}, "success": True},
    )
    httpx_mock.add_response(
        url=BASE,
        method="GET",
        match_params={"start": "1", "limit": "100"},
        json={"data": [{"id": "uuid-1"}], "pagination": {"hasNextPage": False}, "success": True},
    )
    result = await call_tool(mcp, "list_environments")
    assert [e["id"] for e in result["data"]] == ["0", "uuid-1"]
    assert len(httpx_mock.get_requests()) == 2


@pytest.mark.asyncio
async def test_get_environment(mcp: Any, httpx_mock: Any) -> None:
    """get_environment wraps the agent in a credential-sensitive envelope."""
    httpx_mock.add_response(
        url=f"{BASE}/0",
        method="GET",
        json={"id": "0", "name": "local"},
    )
    result = await call_tool(mcp, "get_environment", env_id="0")
    assert result["classification"] == "credential_sensitive"
    assert "warning" in result
    assert result["data"]["id"] == "0"


@pytest.mark.asyncio
async def test_create_environment(mcp: Any, httpx_mock: Any) -> None:
    """create_environment registers a remote agent on POST /api/agents."""
    httpx_mock.add_response(
        url=BASE,
        method="POST",
        json={"id": "new-uuid", "name": "staging"},
    )
    result = await call_tool(
        mcp,
        "create_environment",
        name="staging",
        api_url="http://remote:3552",
        agent_token="tok_abc",
    )
    assert result["name"] == "staging"

    request = httpx_mock.get_requests()[0]
    assert request.url.path == "/api/agents"
    assert json.loads(request.content) == {
        "name": "staging",
        "apiUrl": "http://remote:3552",
        "accessToken": "tok_abc",
    }


@pytest.mark.asyncio
async def test_update_environment_uses_patch(mcp: Any, httpx_mock: Any) -> None:
    """update_environment sends a partial PATCH, not a PUT."""
    httpx_mock.add_response(
        url=f"{BASE}/0",
        method="PATCH",
        json={"id": "0", "name": "renamed"},
    )
    result = await call_tool(mcp, "update_environment", env_id="0", name="renamed")
    assert result["name"] == "renamed"

    request = httpx_mock.get_requests()[0]
    assert request.method == "PATCH"
    assert json.loads(request.content) == {"name": "renamed"}


@pytest.mark.asyncio
async def test_remove_environment_needs_confirm(mcp: Any, httpx_mock: Any) -> None:
    """remove_environment returns a proposal and touches no endpoint."""
    result = await call_tool(mcp, "remove_environment", env_id="0")
    assert result["action"] == "remove_environment"
    assert result["target"] == "0"
    assert result["classification"] == "destructive_write"
    assert result["confirmation_token"]
    assert result["operation_hash"]
    assert "warning" in result
    assert httpx_mock.get_requests() == []


@pytest.mark.asyncio
async def test_remove_environment_confirmed(ops_mcp: Any, httpx_mock: Any) -> None:
    """remove_environment executes the DELETE after confirm_operation."""
    httpx_mock.add_response(
        url=f"{BASE}/0",
        method="DELETE",
        json={"message": "removed"},
    )
    proposal = await call_tool(ops_mcp, "remove_environment", env_id="0")
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
    assert request.url.path == "/api/agents/0"
    assert request.content == b""
