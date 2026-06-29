"""Tests for volume tools."""
from __future__ import annotations

from typing import Any

import pytest

from tests.conftest import call_tool


@pytest.mark.asyncio
async def test_list_volumes(mcp: Any, httpx_mock: Any) -> None:
    """list_volumes returns volumes list."""
    httpx_mock.add_response(
        url="http://localhost:3552/api/environments/0/volumes",
        method="GET",
        json=[{"name": "data-vol", "driver": "local"}],
    )
    result = await call_tool(mcp, "list_volumes")
    assert result == [{"name": "data-vol", "driver": "local"}]


@pytest.mark.asyncio
async def test_create_volume(mcp: Any, httpx_mock: Any) -> None:
    """create_volume posts with name and driver."""
    httpx_mock.add_response(
        url="http://localhost:3552/api/environments/0/volumes",
        method="POST",
        json={"name": "my-vol", "driver": "local"},
    )
    result = await call_tool(mcp, "create_volume", name="my-vol")
    assert result["name"] == "my-vol"


@pytest.mark.asyncio
async def test_inspect_volume(mcp: Any, httpx_mock: Any) -> None:
    """inspect_volume returns volume details."""
    httpx_mock.add_response(
        url="http://localhost:3552/api/environments/0/volumes/my-vol",
        method="GET",
        json={"name": "my-vol", "mountpoint": "/data"},
    )
    result = await call_tool(mcp, "inspect_volume", name="my-vol")
    assert result["mountpoint"] == "/data"


@pytest.mark.asyncio
async def test_remove_volume_needs_confirm(mcp: Any, httpx_mock: Any) -> None:
    """remove_volume returns warning when not confirmed."""
    result = await call_tool(mcp, "remove_volume", name="my-vol")
    assert "warning" in result


@pytest.mark.asyncio
async def test_remove_volume_confirmed(mcp: Any, httpx_mock: Any) -> None:
    """remove_volume executes when confirmed."""
    httpx_mock.add_response(
        url="http://localhost:3552/api/environments/0/volumes/my-vol",
        method="DELETE",
        json={"message": "removed"},
    )
    result = await call_tool(mcp, "remove_volume", name="my-vol", confirm=True)
    assert result == {"message": "removed"}
