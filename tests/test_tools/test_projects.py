"""Tests for Compose project tools."""

from __future__ import annotations

import json
from typing import Any

import pytest

from arcane_mcp import client
from arcane_mcp.safety import get_token_store
from tests.conftest import call_tool, parse_multipart, register_operations

COMPOSE = "services:\n  a:\n    image: hello-world\n"


@pytest.fixture(autouse=True)
def default_api_v2(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pin Arcane API v2 for the default-path tests.

    Endpoints are resolved at proposal time (they are stored on the
    confirmation token), so without a pinned version the proposal would probe
    ``GET /api/version`` — which breaks the "no HTTP call at proposal time"
    assertions below.
    """
    monkeypatch.setenv("ARCANE_API_VERSION", "2")
    client.reset_version_cache()


@pytest.fixture
def ops_mcp(mcp: Any) -> Any:
    """MCP instance with the safety tools registered (for confirm_operation)."""
    return register_operations(mcp)


# ── read-only tools ───────────────────────────────────────────────────


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
async def test_redeploy_project(mcp: Any, httpx_mock: Any) -> None:
    """redeploy_project posts to redeploy endpoint."""
    httpx_mock.add_response(
        url="http://localhost:3552/api/environments/0/projects/p1/redeploy",
        method="POST",
        json={"message": "redeployed"},
    )
    result = await call_tool(mcp, "redeploy_project", project_id="p1")
    assert result == {"message": "redeployed"}


# ── deploy_project ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_deploy_project_proposes(mcp: Any, httpx_mock: Any) -> None:
    """deploy_project returns a proposal with a token and makes no HTTP call."""
    result = await call_tool(mcp, "deploy_project", compose_content=COMPOSE, project_name="myapp")
    assert result["action"] == "deploy_project"
    assert result["target"] == "myapp"
    assert result["confirmation_token"]
    assert result["operation_hash"]
    assert "plan" in result
    assert httpx_mock.get_requests() == []


@pytest.mark.asyncio
async def test_deploy_project_sends_multipart(ops_mcp: Any, httpx_mock: Any) -> None:
    """Confirmed deploy posts multipart with project/manifest parts."""
    httpx_mock.add_response(
        url="http://localhost:3552/api/environments/0/projects",
        method="POST",
        json={"success": True, "data": {"id": "p1", "name": "myapp"}},
    )

    proposal = await call_tool(ops_mcp, "deploy_project", compose_content=COMPOSE, project_name="myapp")
    result = await call_tool(
        ops_mcp,
        "confirm_operation",
        token=proposal["confirmation_token"],
        operation_hash=proposal["operation_hash"],
    )
    assert result["data"]["id"] == "p1"

    request = httpx_mock.get_requests()[0]
    assert request.headers["content-type"].startswith("multipart/form-data")

    parts = parse_multipart(request)
    assert set(parts) == {"project", "manifest"}

    project = json.loads(parts["project"])
    assert "compose" not in project
    assert project["name"] == "myapp"
    assert project["composeContent"] == COMPOSE

    assert json.loads(parts["manifest"]) == {"fileChanges": []}


# ── remove_project ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_remove_project_needs_confirm(mcp: Any, httpx_mock: Any) -> None:
    """remove_project returns a proposal token without touching the API."""
    result = await call_tool(mcp, "remove_project", project_id="p1")
    assert "warning" in result
    assert result["confirmation_token"]
    assert httpx_mock.get_requests() == []


@pytest.mark.asyncio
async def test_remove_project_confirmed(ops_mcp: Any, httpx_mock: Any) -> None:
    """remove_project executes after confirm_operation."""
    httpx_mock.add_response(
        url="http://localhost:3552/api/environments/0/projects/p1/destroy",
        method="DELETE",
        json={"message": "removed"},
    )
    proposal = await call_tool(ops_mcp, "remove_project", project_id="p1")
    result = await call_tool(
        ops_mcp,
        "confirm_operation",
        token=proposal["confirmation_token"],
        operation_hash=proposal["operation_hash"],
    )
    assert result == {"message": "removed"}


# ── update_project ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_update_project_sends_compose_content_key(ops_mcp: Any, httpx_mock: Any) -> None:
    """update_project sends composeContent (never compose) as JSON."""
    httpx_mock.add_response(
        url="http://localhost:3552/api/environments/0/projects/p1",
        method="PUT",
        json={"success": True, "data": {"id": "p1"}},
    )
    proposal = await call_tool(ops_mcp, "update_project", project_id="p1", compose_content=COMPOSE)
    assert "confirmation_token" in proposal

    await call_tool(
        ops_mcp,
        "confirm_operation",
        token=proposal["confirmation_token"],
        operation_hash=proposal["operation_hash"],
    )

    request = httpx_mock.get_requests()[0]
    assert request.headers["content-type"].startswith("application/json")
    body = json.loads(request.content)
    assert body == {"composeContent": COMPOSE}
    assert "compose" not in body


@pytest.mark.asyncio
async def test_update_project_name_only(ops_mcp: Any, httpx_mock: Any) -> None:
    """A name-only update sends only the name key."""
    httpx_mock.add_response(
        url="http://localhost:3552/api/environments/0/projects/p1",
        method="PUT",
        json={"success": True, "data": {"id": "p1", "name": "renamed"}},
    )
    proposal = await call_tool(ops_mcp, "update_project", project_id="p1", project_name="renamed")
    result = await call_tool(
        ops_mcp,
        "confirm_operation",
        token=proposal["confirmation_token"],
        operation_hash=proposal["operation_hash"],
    )
    assert result["data"]["name"] == "renamed"

    body = json.loads(httpx_mock.get_requests()[0].content)
    assert body == {"name": "renamed"}


@pytest.mark.asyncio
async def test_update_project_empty_payload(mcp: Any, httpx_mock: Any) -> None:
    """update_project returns warning with no update fields."""
    result = await call_tool(mcp, "update_project", project_id="p1")
    assert "warning" in result


# ── Arcane v3 (agents routes) ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_deploy_project_v3_uses_agents_endpoint(mcp: Any, httpx_mock: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    """On v3 the deploy proposal targets /api/agents/{env}/projects, no HTTP call."""
    monkeypatch.setenv("ARCANE_API_VERSION", "3")
    proposal = await call_tool(mcp, "deploy_project", compose_content=COMPOSE, project_name="myapp")
    entry = get_token_store().peek(proposal["confirmation_token"])
    assert entry is not None
    assert entry["endpoint"] == "/api/agents/0/projects"
    assert entry["method"] == "POST"
    assert httpx_mock.get_requests() == []


@pytest.mark.asyncio
async def test_update_project_v3_uses_patch(mcp: Any, httpx_mock: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    """On v3 the update proposal targets /api/agents/... and uses PATCH."""
    monkeypatch.setenv("ARCANE_API_VERSION", "3")
    proposal = await call_tool(mcp, "update_project", project_id="p1", compose_content=COMPOSE)
    entry = get_token_store().peek(proposal["confirmation_token"])
    assert entry is not None
    assert entry["endpoint"] == "/api/agents/0/projects/p1"
    assert entry["method"] == "PATCH"
    assert httpx_mock.get_requests() == []


@pytest.mark.asyncio
async def test_read_tool_v3_uses_agents_endpoint(mcp: Any, httpx_mock: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    """Read tools follow the detected prefix too."""
    monkeypatch.setenv("ARCANE_API_VERSION", "3")
    httpx_mock.add_response(
        url="http://localhost:3552/api/agents/0/projects",
        method="GET",
        json=[{"id": "p1", "name": "myapp"}],
    )
    result = await call_tool(mcp, "list_projects")
    assert result == [{"id": "p1", "name": "myapp"}]
