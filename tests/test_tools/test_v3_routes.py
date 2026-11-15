"""Tests pinning the Arcane 3 routes that moved beyond the /environments -> /agents rename."""
from __future__ import annotations

from typing import Any

import pytest
from fastmcp import FastMCP

from arcane_mcp.tools import activities, vulnerabilities
from tests.conftest import call_tool

BASE = "http://localhost:3552"


@pytest.fixture
def mcp_extra(mcp: FastMCP) -> FastMCP:
    """The shared FastMCP instance plus the modules conftest does not register."""
    activities.register(mcp)
    vulnerabilities.register(mcp)
    return mcp


@pytest.mark.asyncio
async def test_get_image_update_summary(mcp: Any, httpx_mock: Any) -> None:
    httpx_mock.add_response(
        url=f"{BASE}/api/agents/0/images/updates/summary", method="GET", json={"totalImages": 3}
    )
    result = await call_tool(mcp, "get_image_update_summary")
    assert result == {"totalImages": 3}


@pytest.mark.asyncio
async def test_check_image_update_uses_image_ref(mcp: Any, httpx_mock: Any) -> None:
    httpx_mock.add_response(
        url=f"{BASE}/api/agents/0/images/updates/check?imageRef=nginx%3A1.27",
        method="GET",
        json={"hasUpdate": False},
    )
    result = await call_tool(mcp, "check_image_update", reference="nginx:1.27")
    assert result == {"hasUpdate": False}


@pytest.mark.asyncio
async def test_check_all_image_updates_action(mcp: Any, httpx_mock: Any) -> None:
    httpx_mock.add_response(
        url=f"{BASE}/api/agents/0/images/updates/check?action=all", method="POST", json={"checked": 5}
    )
    result = await call_tool(mcp, "check_all_image_updates")
    assert result == {"checked": 5}


@pytest.mark.asyncio
async def test_get_environment_events(mcp_extra: Any, httpx_mock: Any) -> None:
    httpx_mock.add_response(url=f"{BASE}/api/events/agent/env-1", method="GET", json={"data": []})
    result = await call_tool(mcp_extra, "get_environment_events", environment_id="env-1")
    assert result == {"data": []}


@pytest.mark.asyncio
async def test_get_scanner_status(mcp_extra: Any, httpx_mock: Any) -> None:
    httpx_mock.add_response(
        url=f"{BASE}/api/agents/0/vulnerabilities/scanner", method="GET", json={"available": True}
    )
    result = await call_tool(mcp_extra, "get_scanner_status")
    assert result == {"available": True}


@pytest.mark.asyncio
async def test_get_project_file_reads_workspace(mcp: Any, httpx_mock: Any) -> None:
    httpx_mock.add_response(
        url=f"{BASE}/api/agents/0/projects/p1/workspace/file?relativePath=compose.yaml",
        method="GET",
        json={"content": "services: {}"},
    )
    result = await call_tool(mcp, "get_project_file", project_id="p1")
    assert result["data"] == {"content": "services: {}"}


@pytest.mark.asyncio
async def test_project_down_confirms_with_action_param(mcp: Any, httpx_mock: Any) -> None:
    httpx_mock.add_response(
        url=f"{BASE}/api/agents/0/projects/p1?action=down", method="POST", json={"message": "down"}
    )
    proposal = await call_tool(mcp, "project_down", project_id="p1")
    result = await call_tool(
        mcp, "confirm_operation",
        token=proposal["confirmation_token"], operation_hash=proposal["operation_hash"],
    )
    assert result == {"message": "down"}


@pytest.mark.asyncio
async def test_volume_writes_are_unsupported(mcp: Any, httpx_mock: Any) -> None:
    result = await call_tool(mcp, "create_volume_directory", name="v", path="/x")
    assert "Arcane >= 3.0" in result["error"]
