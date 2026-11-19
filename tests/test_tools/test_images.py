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


@pytest.mark.asyncio
async def test_list_images(mcp: Any, httpx_mock: Any) -> None:
    """list_images returns images list."""
    httpx_mock.add_response(
        url="http://localhost:3552/api/environments/0/images",
        method="GET",
        json=[{"id": "img1", "repo": "nginx"}],
    )
    result = await call_tool(mcp, "list_images")
    assert result == [{"id": "img1", "repo": "nginx"}]


@pytest.mark.asyncio
async def test_pull_image(mcp: Any, httpx_mock: Any) -> None:
    """pull_image sends pull request."""
    httpx_mock.add_response(
        url="http://localhost:3552/api/environments/0/images/pull",
        method="POST",
        json={"status": "pulling"},
    )
    result = await call_tool(mcp, "pull_image", repository="nginx", tag="latest")
    assert result == {"status": "pulling"}


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
        url="http://localhost:3552/api/environments/0/images/img1",
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
    assert request.url.path == "/api/environments/0/images/img1"
    assert json.loads(request.content) == {"force": "false"}


@pytest.mark.asyncio
async def test_inspect_image(mcp: Any, httpx_mock: Any) -> None:
    """inspect_image returns image details."""
    httpx_mock.add_response(
        url="http://localhost:3552/api/environments/0/images/img1",
        method="GET",
        json={"id": "img1", "repo": "nginx"},
    )
    result = await call_tool(mcp, "inspect_image", image_id="img1")
    assert result["id"] == "img1"


@pytest.mark.asyncio
async def test_tag_image(mcp: Any, httpx_mock: Any) -> None:
    """tag_image tags an existing image."""
    httpx_mock.add_response(
        url="http://localhost:3552/api/environments/0/images/img1/tag",
        method="POST",
        json={"message": "tagged"},
    )
    result = await call_tool(mcp, "tag_image", source="img1", target="myrepo/app:latest")
    assert result == {"message": "tagged"}
