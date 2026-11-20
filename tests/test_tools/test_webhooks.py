"""Tests for webhook tools."""

from __future__ import annotations

import json
from typing import Any

import pytest

from tests.conftest import call_tool, register_operations

BASE = "http://localhost:3552"
WEBHOOKS = f"{BASE}/api/agents/0/webhooks"


def request_body(request: Any) -> Any:
    """Decode a mocked request's JSON body (httpx.Request has no ``.json()``)."""
    return json.loads(request.content)


@pytest.mark.asyncio
async def test_trigger_webhook_removed_in_v3(mcp: Any, httpx_mock: Any) -> None:
    """trigger_webhook is a notice in v3: it must not issue any request."""
    result = await call_tool(mcp, "trigger_webhook", token="tok_abc", action="deploy")
    assert "removed" in result["error"]
    assert result["requested"] == {"token": "tok_abc", "action": "deploy"}
    assert httpx_mock.get_requests() == []


@pytest.mark.asyncio
async def test_list_webhooks_paginates(mcp: Any, httpx_mock: Any) -> None:
    """list_webhooks walks every page via paginate_all."""
    httpx_mock.add_response(
        url=f"{WEBHOOKS}?start=0&limit=100",
        method="GET",
        json={
            "data": [{"id": "w1", "name": "one"}],
            "pagination": {"hasNextPage": True, "totalItems": 2},
            "success": True,
        },
    )
    httpx_mock.add_response(
        url=f"{WEBHOOKS}?start=1&limit=100",
        method="GET",
        json={
            "data": [{"id": "w2", "name": "two"}],
            "pagination": {"hasNextPage": False, "totalItems": 2},
            "success": True,
        },
    )
    result = await call_tool(mcp, "list_webhooks")
    assert [w["id"] for w in result["data"]] == ["w1", "w2"]
    assert result["pagination"]["totalItems"] == 2

    requests = httpx_mock.get_requests()
    assert len(requests) == 2
    assert [r.url.params["start"] for r in requests] == ["0", "1"]
    assert all(r.url.params["limit"] == "100" for r in requests)


@pytest.mark.asyncio
async def test_create_webhook_sends_v3_body(mcp: Any, httpx_mock: Any) -> None:
    """create_webhook posts a Webhook body (targetType/actionType), not a url."""
    httpx_mock.add_response(
        url=WEBHOOKS,
        method="POST",
        json={"id": "w3", "token": "wh_tok", "name": "deploy"},
    )
    result = await call_tool(
        mcp,
        "create_webhook",
        name="deploy",
        target_type="container",
        action_type="restart",
        target_id="abc123",
    )
    assert result["token"] == "wh_tok"

    body = request_body(httpx_mock.get_request())
    assert body == {
        "name": "deploy",
        "targetType": "container",
        "actionType": "restart",
        "targetId": "abc123",
    }


@pytest.mark.asyncio
async def test_update_webhook_uses_patch(mcp: Any, httpx_mock: Any) -> None:
    """update_webhook PATCHes the webhook's enabled flag."""
    httpx_mock.add_response(
        url=f"{WEBHOOKS}/w1",
        method="PATCH",
        json={"id": "w1", "enabled": False},
    )
    result = await call_tool(mcp, "update_webhook", webhook_id="w1", enabled=False)
    assert result["enabled"] is False
    assert request_body(httpx_mock.get_request()) == {"enabled": False}


@pytest.mark.asyncio
async def test_delete_webhook_proposes_without_request(mcp: Any, httpx_mock: Any) -> None:
    """delete_webhook returns a token and sends nothing."""
    ops_mcp = register_operations(mcp)
    result = await call_tool(ops_mcp, "delete_webhook", webhook_id="w1")
    assert result["action"] == "delete_webhook"
    assert result["confirmation_token"]
    assert httpx_mock.get_requests() == []
