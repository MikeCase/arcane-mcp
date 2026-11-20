"""Tests for registries, vulnerabilities and ports tools (v3 routes).

These modules are not part of the shared ``mcp`` fixture, so this file registers
its own instance.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from fastmcp import FastMCP

from arcane_mcp.safety import get_token_store
from arcane_mcp.tools import ports, registries, vulnerabilities
from tests.conftest import call_tool, register_operations

BASE = "http://localhost:3552"
AGENT = f"{BASE}/api/agents/0"


def request_body(request: Any) -> Any:
    """Decode a mocked request's JSON body (httpx.Request has no ``.json()``)."""
    return json.loads(request.content)


@pytest.fixture
def v3_mcp() -> FastMCP:
    """FastMCP instance with the registries, vulnerabilities and ports tools."""
    mcp = FastMCP("test-arcane-registries")
    registries.register(mcp)
    vulnerabilities.register(mcp)
    ports.register(mcp)
    return mcp


# ── registries: global ``/api/registries`` ──


@pytest.mark.asyncio
async def test_list_registries_is_global_and_paginated(v3_mcp: FastMCP, httpx_mock: Any) -> None:
    """list_registries hits /api/registries (no env_id) and walks pages."""
    url = f"{BASE}/api/registries"
    httpx_mock.add_response(
        url=f"{url}?start=0&limit=100",
        method="GET",
        json={"data": [{"id": "r1"}], "pagination": {"hasNextPage": True}, "success": True},
    )
    httpx_mock.add_response(
        url=f"{url}?start=1&limit=100",
        method="GET",
        json={"data": [{"id": "r2"}], "pagination": {"hasNextPage": False}, "success": True},
    )
    result = await call_tool(v3_mcp, "list_registries")
    assert [r["id"] for r in result["data"]] == ["r1", "r2"]

    requests = httpx_mock.get_requests()
    assert len(requests) == 2
    assert [r.url.params["start"] for r in requests] == ["0", "1"]
    assert all("/api/agents/" not in str(r.url) for r in requests)


@pytest.mark.asyncio
async def test_get_registry_path(v3_mcp: FastMCP, httpx_mock: Any) -> None:
    """get_registry reads /api/registries/{id}."""
    httpx_mock.add_response(url=f"{BASE}/api/registries/r1", method="GET", json={"id": "r1"})
    result = await call_tool(v3_mcp, "get_registry", registry_id="r1")
    assert result == {"id": "r1"}


@pytest.mark.asyncio
async def test_create_registry_maps_name_and_password(v3_mcp: FastMCP, httpx_mock: Any) -> None:
    """create_registry sends description/token (v3 ContainerRegistry field names)."""
    httpx_mock.add_response(url=f"{BASE}/api/registries", method="POST", json={"id": "r9"})
    await call_tool(
        v3_mcp,
        "create_registry",
        name="dockerhub",
        url="https://registry-1.docker.io",
        username="me",
        password="s3cret",
    )
    body = request_body(httpx_mock.get_request())
    assert body == {
        "url": "https://registry-1.docker.io",
        "description": "dockerhub",
        "username": "me",
        "token": "s3cret",
    }


@pytest.mark.asyncio
async def test_update_registry_uses_patch(v3_mcp: FastMCP, httpx_mock: Any) -> None:
    """update_registry PATCHes /api/registries/{id}."""
    httpx_mock.add_response(url=f"{BASE}/api/registries/r1", method="PATCH", json={"id": "r1"})
    await call_tool(v3_mcp, "update_registry", registry_id="r1", name="renamed")
    request = httpx_mock.get_request()
    assert request.method == "PATCH"
    assert request_body(request) == {"description": "renamed"}


@pytest.mark.asyncio
async def test_test_registry_uses_action_query(v3_mcp: FastMCP, httpx_mock: Any) -> None:
    """test_registry is POST /api/registries/{id}?action=test."""
    httpx_mock.add_response(
        url=f"{BASE}/api/registries/r1?action=test",
        method="POST",
        json={"message": "ok"},
    )
    result = await call_tool(v3_mcp, "test_registry", registry_id="r1")
    assert result == {"message": "ok"}
    assert httpx_mock.get_request().url.params["action"] == "test"


@pytest.mark.asyncio
async def test_delete_registry_proposes_without_request(v3_mcp: FastMCP, httpx_mock: Any) -> None:
    """delete_registry keeps the confirm-token flow and sends nothing."""
    ops_mcp = register_operations(v3_mcp)
    result = await call_tool(ops_mcp, "delete_registry", registry_id="r1")
    assert result["confirmation_token"]
    assert result["operation_hash"]
    assert httpx_mock.get_requests() == []


# ── vulnerabilities ──


@pytest.mark.asyncio
async def test_summary_uses_vulnerabilities_summary(v3_mcp: FastMCP, httpx_mock: Any) -> None:
    """get_vulnerability_summary_all reads /vulnerabilities/summary."""
    httpx_mock.add_response(
        url=f"{AGENT}/vulnerabilities/summary",
        method="GET",
        json={"totalVulnerabilities": 7},
    )
    result = await call_tool(v3_mcp, "get_vulnerability_summary_all")
    assert result["totalVulnerabilities"] == 7


@pytest.mark.asyncio
async def test_list_all_vulnerabilities_paginates(v3_mcp: FastMCP, httpx_mock: Any) -> None:
    """list_all_vulnerabilities walks /vulnerabilities/all pages."""
    url = f"{AGENT}/vulnerabilities/all"
    httpx_mock.add_response(
        url=f"{url}?start=0&limit=100",
        method="GET",
        json={"data": [{"id": "v1"}], "pagination": {"hasNextPage": True}, "success": True},
    )
    httpx_mock.add_response(
        url=f"{url}?start=1&limit=100",
        method="GET",
        json={"data": [{"id": "v2"}], "pagination": {"hasNextPage": False}, "success": True},
    )
    result = await call_tool(v3_mcp, "list_all_vulnerabilities")
    assert [v["id"] for v in result["data"]] == ["v1", "v2"]
    assert len(httpx_mock.get_requests()) == 2


@pytest.mark.asyncio
async def test_ignore_vulnerability_posts_ignored_collection(v3_mcp: FastMCP, httpx_mock: Any) -> None:
    """ignore_vulnerability POSTs the IgnoredVulnerability triple to /ignored."""
    httpx_mock.add_response(
        url=f"{AGENT}/vulnerabilities/ignored",
        method="POST",
        json={"id": "ign1"},
    )
    result = await call_tool(
        v3_mcp,
        "ignore_vulnerability",
        image_id="sha256:abc123",
        vulnerability_id="CVE-2023-1234",
        pkg_name="openssl",
        reason="False positive",
    )
    assert result == {"id": "ign1"}
    assert request_body(httpx_mock.get_request()) == {
        "imageId": "sha256:abc123",
        "vulnerabilityId": "CVE-2023-1234",
        "pkgName": "openssl",
        "reason": "False positive",
    }


@pytest.mark.asyncio
async def test_list_ignored_vulnerabilities_paginates(v3_mcp: FastMCP, httpx_mock: Any) -> None:
    """list_ignored_vulnerabilities reads /vulnerabilities/ignored."""
    url = f"{AGENT}/vulnerabilities/ignored"
    httpx_mock.add_response(
        url=f"{url}?start=0&limit=100",
        method="GET",
        json={"data": [{"id": "ign1"}], "pagination": {"hasNextPage": False}, "success": True},
    )
    result = await call_tool(v3_mcp, "list_ignored_vulnerabilities")
    assert [i["id"] for i in result["data"]] == ["ign1"]
    assert httpx_mock.get_request().url.params["start"] == "0"


@pytest.mark.asyncio
async def test_unignore_vulnerability_proposal_path(v3_mcp: FastMCP, httpx_mock: Any) -> None:
    """unignore_vulnerability proposes DELETE /vulnerabilities/ignored/{ignoreId}."""
    ops_mcp = register_operations(v3_mcp)
    result = await call_tool(ops_mcp, "unignore_vulnerability", ignore_id="ign1")
    assert result["confirmation_token"]
    assert httpx_mock.get_requests() == []

    record = get_token_store().peek(result["confirmation_token"])
    assert record is not None
    assert record["endpoint"] == "/api/agents/0/vulnerabilities/ignored/ign1"
    assert record["method"] == "DELETE"


@pytest.mark.asyncio
async def test_scanner_status_uses_scanner_path(v3_mcp: FastMCP, httpx_mock: Any) -> None:
    """get_scanner_status reads /vulnerabilities/scanner."""
    httpx_mock.add_response(
        url=f"{AGENT}/vulnerabilities/scanner",
        method="GET",
        json={"available": True, "version": "0.50.0"},
    )
    result = await call_tool(v3_mcp, "get_scanner_status")
    assert result["available"] is True


# ── ports ──


@pytest.mark.asyncio
async def test_list_ports_paginates(v3_mcp: FastMCP, httpx_mock: Any) -> None:
    """list_ports reads the paginated /agents/{id}/ports."""
    url = f"{AGENT}/ports"
    httpx_mock.add_response(
        url=f"{url}?start=0&limit=100",
        method="GET",
        json={"data": [{"id": "p1"}], "pagination": {"hasNextPage": False}, "success": True},
    )
    result = await call_tool(v3_mcp, "list_ports")
    assert [p["id"] for p in result["data"]] == ["p1"]
    assert httpx_mock.get_request().url.params["limit"] == "100"
