"""Tests for environment tools."""
from __future__ import annotations

from typing import Any

import pytest

from tests.conftest import call_tool


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
    """get_environment returns a single environment."""
    httpx_mock.add_response(
        url="http://localhost:3552/api/environments/0",
        method="GET",
        json={"id": "0", "name": "local"},
    )
    result = await call_tool(mcp, "get_environment", env_id="0")
    assert result["id"] == "0"


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
    """remove_environment returns warning when not confirmed."""
    result = await call_tool(mcp, "remove_environment", env_id="0")
    assert "warning" in result


@pytest.mark.asyncio
async def test_remove_environment_confirmed(mcp: Any, httpx_mock: Any) -> None:
    """remove_environment executes when confirmed."""
    httpx_mock.add_response(
        url="http://localhost:3552/api/environments/0",
        method="DELETE",
        json={"message": "removed"},
    )
    result = await call_tool(mcp, "remove_environment", env_id="0", confirm=True)
    assert result == {"message": "removed"}
