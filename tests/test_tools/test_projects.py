"""Tests for Compose project tools.

Targets Arcane v3+ only: routes live under ``/api/agents/{env_id}``, project
actions travel as an ``action`` query parameter, and up/redeploy/pull share
``POST /projects/{projectId}/deploy``.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from arcane_mcp.safety import get_token_store
from tests.conftest import call_tool, parse_multipart, register_operations

BASE = "http://localhost:3552/api/agents/0"
COMPOSE = "services:\n  a:\n    image: hello-world\n"


@pytest.fixture(autouse=True)
def pin_api_v3(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pin the API version for the suite.

    Routes no longer branch on the version (v2 is gone), but pinning keeps a
    stray ``detect_api_version()`` call from probing ``GET /api/version`` and
    consuming an ``httpx_mock`` response.
    """
    monkeypatch.setenv("ARCANE_API_VERSION", "3")


@pytest.fixture
def ops_mcp(mcp: Any) -> Any:
    """MCP instance with the safety tools registered (for confirm_operation)."""
    return register_operations(mcp)


# ── read-only tools ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_projects(mcp: Any, httpx_mock: Any) -> None:
    """list_projects walks the paginated collection and returns the envelope."""
    httpx_mock.add_response(
        url=f"{BASE}/projects?start=0&limit=100",
        method="GET",
        json={"data": [{"id": "p1", "name": "myapp"}], "pagination": {"hasNextPage": False}},
    )
    result = await call_tool(mcp, "list_projects")
    assert result["data"] == [{"id": "p1", "name": "myapp"}]

    request = httpx_mock.get_requests()[0]
    assert request.url.params["start"] == "0"
    assert request.url.params["limit"] == "100"


@pytest.mark.asyncio
async def test_list_projects_follows_pages(mcp: Any, httpx_mock: Any) -> None:
    """list_projects does not silently stop at the first 20-item page."""
    httpx_mock.add_response(
        url=f"{BASE}/projects?start=0&limit=100",
        method="GET",
        json={
            "data": [{"id": f"p{i}"} for i in range(20)],
            "pagination": {"hasNextPage": True},
        },
    )
    httpx_mock.add_response(
        url=f"{BASE}/projects?start=20&limit=100",
        method="GET",
        json={"data": [{"id": f"p{i}"} for i in range(20, 25)], "pagination": {"hasNextPage": False}},
    )
    result = await call_tool(mcp, "list_projects")
    assert len(result["data"]) == 25
    assert result["pagination"]["totalItems"] == 25

    requests = httpx_mock.get_requests()
    assert len(requests) == 2
    assert requests[0].url.params["start"] == "0"
    assert requests[1].url.params["start"] == "20"


@pytest.mark.asyncio
async def test_get_project(mcp: Any, httpx_mock: Any) -> None:
    """get_project returns project details."""
    httpx_mock.add_response(
        url=f"{BASE}/projects/p1",
        method="GET",
        json={"id": "p1", "name": "myapp"},
    )
    result = await call_tool(mcp, "get_project", project_id="p1")
    assert result["id"] == "p1"


@pytest.mark.asyncio
async def test_get_project_counts(mcp: Any, httpx_mock: Any) -> None:
    """get_project_counts hits the v3 counts route."""
    httpx_mock.add_response(
        url=f"{BASE}/projects/counts",
        method="GET",
        json={"running": 1, "stopped": 2},
    )
    result = await call_tool(mcp, "get_project_counts")
    assert result == {"running": 1, "stopped": 2}


@pytest.mark.asyncio
async def test_get_project_compose(mcp: Any, httpx_mock: Any) -> None:
    """get_project_compose returns the compose payload under a sensitivity warning."""
    httpx_mock.add_response(
        url=f"{BASE}/projects/p1/compose",
        method="GET",
        json={"composeContent": COMPOSE},
    )
    result = await call_tool(mcp, "get_project_compose", project_id="p1")
    assert result["data"] == {"composeContent": COMPOSE}
    assert "warning" in result


@pytest.mark.asyncio
async def test_get_project_file_uses_workspace_route(mcp: Any, httpx_mock: Any) -> None:
    """get_project_file reads /workspace/file (v3 moved it off /file)."""
    httpx_mock.add_response(
        url=f"{BASE}/projects/p1/workspace/file",
        method="GET",
        json={"relativePath": "docker-compose.yml", "content": COMPOSE},
    )
    result = await call_tool(mcp, "get_project_file", project_id="p1")
    assert result["data"]["content"] == COMPOSE
    assert httpx_mock.get_requests()[0].url.path == "/api/agents/0/projects/p1/workspace/file"


@pytest.mark.asyncio
async def test_get_project_runtime(mcp: Any, httpx_mock: Any) -> None:
    """get_project_runtime is unchanged on v3."""
    httpx_mock.add_response(
        url=f"{BASE}/projects/p1/runtime",
        method="GET",
        json={"status": "running"},
    )
    assert await call_tool(mcp, "get_project_runtime", project_id="p1") == {"status": "running"}


# ── deploy / redeploy / pull ──────────────────────────────────────────


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

    entry = get_token_store().peek(result["confirmation_token"])
    assert entry is not None
    assert entry["endpoint"] == "/api/agents/0/projects"
    assert entry["method"] == "POST"
    assert entry["encoding"] == "multipart"


@pytest.mark.asyncio
async def test_deploy_project_sends_multipart(ops_mcp: Any, httpx_mock: Any) -> None:
    """Confirmed deploy posts multipart with project/manifest parts."""
    httpx_mock.add_response(
        url=f"{BASE}/projects",
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


@pytest.mark.asyncio
async def test_redeploy_project(mcp: Any, httpx_mock: Any) -> None:
    """redeploy posts to /deploy?action=redeploy with build enabled and parses the stream."""
    httpx_mock.add_response(
        url=f"{BASE}/projects/p1/deploy?action=redeploy",
        method="POST",
        content=b'{"activityId":"a1","type":"activity"}\n{"log":"recreated"}\n{"done":true}\n',
        headers={"content-type": "application/x-json-stream"},
    )
    result = await call_tool(mcp, "redeploy_project", project_id="p1")
    assert result["success"] is True
    assert result["activityId"] == "a1"
    assert result["logs"] == ["recreated"]
    assert result["done"] is True

    request = httpx_mock.get_requests()[0]
    assert request.url.params["action"] == "redeploy"
    assert json.loads(request.content) == {"build": True}


@pytest.mark.asyncio
async def test_pull_project_images(mcp: Any, httpx_mock: Any) -> None:
    """pull posts to /deploy?action=pull with an empty options body."""
    httpx_mock.add_response(
        url=f"{BASE}/projects/p1/deploy?action=pull",
        method="POST",
        content=b'{"log":"pulled"}\n{"done":true}\n',
        headers={"content-type": "application/x-json-stream"},
    )
    result = await call_tool(mcp, "pull_project_images", project_id="p1")
    assert result["logs"] == ["pulled"]
    assert result["done"] is True

    request = httpx_mock.get_requests()[0]
    assert request.url.params["action"] == "pull"
    assert json.loads(request.content) == {}


@pytest.mark.asyncio
async def test_build_project(mcp: Any, httpx_mock: Any) -> None:
    """build keeps its own route and stream parsing."""
    httpx_mock.add_response(
        url=f"{BASE}/projects/p1/build",
        method="POST",
        content=b'{"log":"built"}\n{"done":true}\n',
        headers={"content-type": "application/x-json-stream"},
    )
    result = await call_tool(mcp, "build_project", project_id="p1")
    assert result["logs"] == ["built"]
    assert httpx_mock.get_requests()[0].url.path == "/api/agents/0/projects/p1/build"


# ── project actions as query params ───────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.parametrize("tool_name", ["project_down", "restart_project"])
async def test_action_tools_propose_with_token(mcp: Any, httpx_mock: Any, tool_name: str) -> None:
    """Token-gated actions propose the v3 path plus their action param, no HTTP call."""
    expected_action = {"project_down": "down", "restart_project": "restart"}[tool_name]
    result = await call_tool(mcp, tool_name, project_id="p1")
    assert result["action"] == tool_name
    assert result["target"] == "p1"
    assert result["confirmation_token"]
    assert httpx_mock.get_requests() == []

    entry = get_token_store().peek(result["confirmation_token"])
    assert entry is not None
    assert entry["endpoint"] == "/api/agents/0/projects/p1"
    assert entry["method"] == "POST"
    assert entry["params"] == {"action": expected_action}


@pytest.mark.asyncio
@pytest.mark.parametrize("tool_name", ["project_down", "restart_project"])
async def test_action_tools_confirmed(ops_mcp: Any, httpx_mock: Any, tool_name: str) -> None:
    """Confirmed actions replay the action query parameter."""
    expected_action = {"project_down": "down", "restart_project": "restart"}[tool_name]
    httpx_mock.add_response(
        url=f"{BASE}/projects/p1?action={expected_action}",
        method="POST",
        json={"success": True},
    )
    proposal = await call_tool(ops_mcp, tool_name, project_id="p1")
    result = await call_tool(
        ops_mcp,
        "confirm_operation",
        token=proposal["confirmation_token"],
        operation_hash=proposal["operation_hash"],
    )
    assert result == {"success": True}

    request = httpx_mock.get_requests()[0]
    assert request.method == "POST"
    assert request.url.path == "/api/agents/0/projects/p1"
    assert request.url.params["action"] == expected_action


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("tool_name", "action"),
    [("archive_project", "archive"), ("unarchive_project", "unarchive")],
)
async def test_archive_tools_use_action_param(mcp: Any, httpx_mock: Any, tool_name: str, action: str) -> None:
    """archive/unarchive moved from sub-paths to ?action=..."""
    httpx_mock.add_response(
        url=f"{BASE}/projects/p1?action={action}",
        method="POST",
        json={"archived": action == "archive"},
    )
    result = await call_tool(mcp, tool_name, project_id="p1")
    assert "archived" in result

    request = httpx_mock.get_requests()[0]
    assert request.url.path == "/api/agents/0/projects/p1"
    assert request.url.params["action"] == action


@pytest.mark.asyncio
async def test_update_project_services_uses_action_param(mcp: Any, httpx_mock: Any) -> None:
    """update_project_services is ?action=updateservices with no services filter."""
    httpx_mock.add_response(
        url=f"{BASE}/projects/p1?action=updateservices",
        method="POST",
        json={"success": True},
    )
    result = await call_tool(mcp, "update_project_services", project_id="p1")
    assert result == {"success": True}

    request = httpx_mock.get_requests()[0]
    assert request.url.params["action"] == "updateservices"
    assert "services" not in request.url.params


# ── remove_project ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_remove_project_needs_confirm(mcp: Any, httpx_mock: Any) -> None:
    """remove_project returns a proposal token without touching the API."""
    result = await call_tool(mcp, "remove_project", project_id="p1")
    assert "warning" in result
    assert result["confirmation_token"]
    assert result["operation_hash"]
    assert httpx_mock.get_requests() == []

    entry = get_token_store().peek(result["confirmation_token"])
    assert entry is not None
    assert entry["endpoint"] == "/api/agents/0/projects/p1"
    assert entry["method"] == "DELETE"
    assert entry["params"] is None


@pytest.mark.asyncio
async def test_remove_project_confirmed(ops_mcp: Any, httpx_mock: Any) -> None:
    """remove_project destroys the resource with a plain DELETE /projects/{id}."""
    httpx_mock.add_response(
        url=f"{BASE}/projects/p1",
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

    request = httpx_mock.get_requests()[0]
    assert request.method == "DELETE"
    assert request.url.path == "/api/agents/0/projects/p1"
    assert "destroy" not in request.url.path


# ── update_project ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_update_project_sends_compose_content_key(ops_mcp: Any, httpx_mock: Any) -> None:
    """update_project PATCHes composeContent (never compose) as JSON."""
    httpx_mock.add_response(
        url=f"{BASE}/projects/p1",
        method="PATCH",
        json={"success": True, "data": {"id": "p1"}},
    )
    proposal = await call_tool(ops_mcp, "update_project", project_id="p1", compose_content=COMPOSE)
    assert "confirmation_token" in proposal

    entry = get_token_store().peek(proposal["confirmation_token"])
    assert entry is not None
    assert entry["endpoint"] == "/api/agents/0/projects/p1"
    assert entry["method"] == "PATCH"

    await call_tool(
        ops_mcp,
        "confirm_operation",
        token=proposal["confirmation_token"],
        operation_hash=proposal["operation_hash"],
    )

    request = httpx_mock.get_requests()[0]
    assert request.method == "PATCH"
    assert request.headers["content-type"].startswith("application/json")
    body = json.loads(request.content)
    assert body == {"composeContent": COMPOSE}
    assert "compose" not in body


@pytest.mark.asyncio
async def test_update_project_name_only(ops_mcp: Any, httpx_mock: Any) -> None:
    """A name-only update sends only the name key."""
    httpx_mock.add_response(
        url=f"{BASE}/projects/p1",
        method="PATCH",
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
    assert httpx_mock.get_requests() == []
