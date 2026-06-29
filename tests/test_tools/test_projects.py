"""Tests for Compose project tools."""
from __future__ import annotations

from typing import Any

import pytest

from tests.conftest import call_tool


@pytest.mark.asyncio
async def test_list_projects(mcp: Any, httpx_mock: Any) -> None:
    """list_projects returns projects list."""
    httpx_mock.add_response(
        url="http://localhost:3552/api/environments/0/projects",
        method="GET",
        json=[{"id": "p1", "name": "myapp"}],
    )
    result = await call_tool(mcp, "list_projects")
    assert result == [{"id": "p1", "name": "myapp"}]


@pytest.mark.asyncio
async def test_get_project(mcp: Any, httpx_mock: Any) -> None:
    """get_project returns project details."""
    httpx_mock.add_response(
        url="http://localhost:3552/api/environments/0/projects/p1",
        method="GET",
        json={"id": "p1", "name": "myapp"},
    )
    result = await call_tool(mcp, "get_project", project_id="p1")
    assert result["id"] == "p1"


@pytest.mark.asyncio
async def test_deploy_project(mcp: Any, httpx_mock: Any) -> None:
    """deploy_project posts compose content."""
    httpx_mock.add_response(
        url="http://localhost:3552/api/environments/0/projects",
        method="POST",
        json={"id": "p1", "name": "myapp"},
    )
    result = await call_tool(mcp, "deploy_project", compose_content="version: '3'", project_name="myapp")
    assert result["id"] == "p1"


@pytest.mark.asyncio
async def test_redeploy_project(mcp: Any, httpx_mock: Any) -> None:
    """redeploy_project posts to redeploy endpoint."""
    httpx_mock.add_response(
        url="http://localhost:3552/api/environments/0/projects/p1/redeploy",
        method="POST",
        json={"message": "redeployed"},
    )
    result = await call_tool(mcp, "redeploy_project", project_id="p1")
    assert result == {"message": "redeployed"}


@pytest.mark.asyncio
async def test_remove_project_needs_confirm(mcp: Any, httpx_mock: Any) -> None:
    """remove_project returns warning when not confirmed."""
    result = await call_tool(mcp, "remove_project", project_id="p1")
    assert "warning" in result


@pytest.mark.asyncio
async def test_remove_project_confirmed(mcp: Any, httpx_mock: Any) -> None:
    """remove_project executes when confirmed."""
    httpx_mock.add_response(
        url="http://localhost:3552/api/environments/0/projects/p1",
        method="DELETE",
        json={"message": "removed"},
    )
    result = await call_tool(mcp, "remove_project", project_id="p1", confirm=True)
    assert result == {"message": "removed"}


@pytest.mark.asyncio
async def test_update_project(mcp: Any, httpx_mock: Any) -> None:
    """update_project sends partial update."""
    httpx_mock.add_response(
        url="http://localhost:3552/api/environments/0/projects/p1",
        method="PUT",
        json={"id": "p1", "name": "renamed"},
    )
    result = await call_tool(mcp, "update_project", project_id="p1", project_name="renamed")
    assert result["name"] == "renamed"


@pytest.mark.asyncio
async def test_update_project_empty_payload(mcp: Any, httpx_mock: Any) -> None:
    """update_project returns warning with no update fields."""
    result = await call_tool(mcp, "update_project", project_id="p1")
    assert "warning" in result
