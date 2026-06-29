"""Tests for image tools."""
from __future__ import annotations

from typing import Any

import pytest

from tests.conftest import call_tool


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
    """remove_image returns warning when not confirmed."""
    result = await call_tool(mcp, "remove_image", image_id="img1")
    assert "warning" in result


@pytest.mark.asyncio
async def test_remove_image_confirmed(mcp: Any, httpx_mock: Any) -> None:
    """remove_image executes when confirmed."""
    httpx_mock.add_response(
        url="http://localhost:3552/api/environments/0/images/img1",
        method="DELETE",
        json={"message": "removed"},
    )
    result = await call_tool(mcp, "remove_image", image_id="img1", confirm=True)
    assert result == {"message": "removed"}


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
