"""Tests for environment tools."""

from __future__ import annotations

from typing import Any

import pytest

from tests.conftest import call_tool, register_operations


@pytest.fixture
def ops_mcp(mcp: Any) -> Any:
    """MCP instance with the safety tools registered (for confirm_operation)."""
    return register_operations(mcp)


@pytest.mark.asyncio
async def test_list_environments(mcp: Any, httpx_mock: Any) -> None:
    """list_environments returns environments list."""
    httpx_mock.add_response(
        url="http://localhost:3552/api/environments",
        method="GET",
        json=[{"id": "0", "name": "local"}, {"id": "uuid-1", "name": "remote"}],
    )
    result = await call_tool(mcp, "list_environments")
    assert len(result) == 2


@pytest.mark.asyncio
async def test_get_environment(mcp: Any, httpx_mock: Any) -> None:
    """get_environment wraps the environment in a credential-sensitive envelope."""
    httpx_mock.add_response(
        url="http://localhost:3552/api/environments/0",
        method="GET",
        json={"id": "0", "name": "local"},
    )
    result = await call_tool(mcp, "get_environment", env_id="0")
    assert result["classification"] == "credential_sensitive"
    assert "warning" in result
    assert result["data"]["id"] == "0"


@pytest.mark.asyncio
async def test_create_environment(mcp: Any, httpx_mock: Any) -> None:
    """create_environment registers a remote agent."""
    httpx_mock.add_response(
        url="http://localhost:3552/api/environments",
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


@pytest.mark.asyncio
async def test_update_environment(mcp: Any, httpx_mock: Any) -> None:
    """update_environment sends partial update."""
    httpx_mock.add_response(
        url="http://localhost:3552/api/environments/0",
        method="PUT",
        json={"id": "0", "name": "renamed"},
    )
    result = await call_tool(mcp, "update_environment", env_id="0", name="renamed")
    assert result["name"] == "renamed"


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
        url="http://localhost:3552/api/environments/0",
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
    assert request.url.path == "/api/environments/0"
    assert request.content == b""
