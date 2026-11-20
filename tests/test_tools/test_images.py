"""Tests for image tools."""

from __future__ import annotations

import json
from typing import Any

import pytest

from tests.conftest import call_tool, register_operations


@pytest.fixture
def ops_mcp(mcp: Any) -> Any:
    """MCP instance with the safety tools registered (for confirm_operation)."""
    return register_operations(mcp)


def _page(data: list[dict[str, Any]], has_next: bool = False) -> dict[str, Any]:
    """Build a v3 paginated envelope."""
    return {
        "data": data,
        "pagination": {"hasNextPage": has_next, "currentPage": 1, "itemsPerPage": len(data)},
        "success": True,
    }


# ── list ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_images_paginates(mcp: Any, httpx_mock: Any) -> None:
    """list_images walks every page instead of stopping at the first 20."""
    first = _page([{"id": "img1", "repo": "nginx"}], has_next=True)
    second = _page([{"id": "img2", "repo": "redis"}])

    httpx_mock.add_response(
        url="http://localhost:3552/api/agents/0/images",
        method="GET",
        match_params={"start": "0", "limit": "100"},
        json=first,
    )
    httpx_mock.add_response(
        url="http://localhost:3552/api/agents/0/images",
        method="GET",
        match_params={"start": "1", "limit": "100"},
        json=second,
    )

    result = await call_tool(mcp, "list_images")

    assert [image["id"] for image in result["data"]] == ["img1", "img2"]
    assert result["pagination"]["totalItems"] == 2
    assert len(httpx_mock.get_requests()) == 2


@pytest.mark.asyncio
async def test_list_images_single_page(mcp: Any, httpx_mock: Any) -> None:
    """A single-page envelope is returned once the server reports no next page."""
    httpx_mock.add_response(
        url="http://localhost:3552/api/agents/0/images",
        method="GET",
        match_params={"start": "0", "limit": "100"},
        json=_page([{"id": "img1", "repo": "nginx"}]),
    )
    result = await call_tool(mcp, "list_images")
    assert result["data"] == [{"id": "img1", "repo": "nginx"}]
    assert httpx_mock.get_requests()[0].url.params["limit"] == "100"


# ── pull / build stream ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_pull_image(mcp: Any, httpx_mock: Any) -> None:
    """pull_image parses the pull action stream."""
    httpx_mock.add_response(
        url="http://localhost:3552/api/agents/0/images/pull",
        method="POST",
        content=b'{"activityId":"a2","type":"activity"}\n{"log":"Pulling nginx"}\n{"done":true}\n',
        headers={"content-type": "application/x-json-stream"},
    )
    result = await call_tool(mcp, "pull_image", repository="nginx", tag="latest")
    assert result["success"] is True
    assert result["activityId"] == "a2"
    assert result["logs"] == ["Pulling nginx"]


# ── remove ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_remove_image_needs_confirm(mcp: Any, httpx_mock: Any) -> None:
    """remove_image returns a proposal and touches no endpoint."""
    result = await call_tool(mcp, "remove_image", image_id="img1")
    assert result["action"] == "remove_image"
    assert result["target"] == "img1"
    assert result["classification"] == "destructive_write"
    assert result["confirmation_token"]
    assert result["operation_hash"]
    assert "warning" in result
    assert httpx_mock.get_requests() == []


@pytest.mark.asyncio
async def test_remove_image_confirmed(ops_mcp: Any, httpx_mock: Any) -> None:
    """remove_image executes the DELETE after confirm_operation."""
    httpx_mock.add_response(
        url="http://localhost:3552/api/agents/0/images/img1",
        method="DELETE",
        json={"message": "removed"},
    )
    proposal = await call_tool(ops_mcp, "remove_image", image_id="img1")
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
    assert request.url.path == "/api/agents/0/images/img1"
    assert json.loads(request.content) == {"force": "false"}


# ── inspect / tag ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_inspect_image(mcp: Any, httpx_mock: Any) -> None:
    """inspect_image returns image details."""
    httpx_mock.add_response(
        url="http://localhost:3552/api/agents/0/images/img1",
        method="GET",
        json={"id": "img1", "repo": "nginx"},
    )
    result = await call_tool(mcp, "inspect_image", image_id="img1")
    assert result["id"] == "img1"


@pytest.mark.asyncio
async def test_tag_image(mcp: Any, httpx_mock: Any) -> None:
    """tag_image tags an existing image."""
    httpx_mock.add_response(
        url="http://localhost:3552/api/agents/0/images/img1/tag",
        method="POST",
        json={"message": "tagged"},
    )
    result = await call_tool(mcp, "tag_image", source="img1", target="myrepo/app:latest")
    assert result == {"message": "tagged"}


# ── image updates (v3 /images/updates/*) ───────────────────────────────


@pytest.mark.asyncio
async def test_check_image_update_by_reference(mcp: Any, httpx_mock: Any) -> None:
    """check_image_update hits GET /images/updates/check with imageRef."""
    httpx_mock.add_response(
        url="http://localhost:3552/api/agents/0/images/updates/check",
        method="GET",
        match_params={"imageRef": "nginx:latest"},
        json={"data": {"imageRef": "nginx:latest", "hasUpdate": True}, "success": True},
    )
    result = await call_tool(mcp, "check_image_update", reference="nginx:latest")
    assert result["data"]["hasUpdate"] is True

    request = httpx_mock.get_requests()[0]
    assert request.url.path == "/api/agents/0/images/updates/check"
    assert request.url.params["imageRef"] == "nginx:latest"
    assert "reference" not in request.url.params


@pytest.mark.asyncio
async def test_check_all_image_updates(mcp: Any, httpx_mock: Any) -> None:
    """check_all_image_updates is POST /images/updates/check?action=all."""
    httpx_mock.add_response(
        url="http://localhost:3552/api/agents/0/images/updates/check",
        method="POST",
        match_params={"action": "all"},
        json={"data": {}, "success": True},
    )
    result = await call_tool(mcp, "check_all_image_updates")
    assert result["success"] is True

    request = httpx_mock.get_requests()[0]
    assert request.method == "POST"
    assert request.url.path == "/api/agents/0/images/updates/check"
    assert request.url.params["action"] == "all"


@pytest.mark.asyncio
async def test_get_image_update_summary(mcp: Any, httpx_mock: Any) -> None:
    """get_image_update_summary reads /images/updates/summary."""
    httpx_mock.add_response(
        url="http://localhost:3552/api/agents/0/images/updates/summary",
        method="GET",
        json={"data": {"totalImages": 100, "imagesWithUpdates": 32}, "success": True},
    )
    result = await call_tool(mcp, "get_image_update_summary")
    assert result["data"]["imagesWithUpdates"] == 32
