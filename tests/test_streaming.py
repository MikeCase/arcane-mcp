"""Tests for the newline-delimited JSON action-stream parser.

Arcane action endpoints (project build/redeploy/pull, image pull/build, volume
backup creation, system upgrade) answer with ``application/x-json-stream`` — an
activity header, one ``{"log": ...}`` line per step, then ``{"done": true}``.
``httpx.Response.json()`` raises ``Extra data: line 2 column 1`` on that body,
so ``client.parse_stream_response`` turns it into a plain dict.  These tests pin
the parser semantics and one tool-level call site.
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from arcane_mcp.client import parse_stream_response
from tests.conftest import call_tool

STREAM = (
    b'{"activityId":"a1","type":"activity"}\n'
    b"\n"
    b'{"log":"#1 [internal] load remote build context"}\n'
    b'{"log":"#1 CACHED"}\n'
    b'{"log":""}\n'
    b'{"done":true}\n'
)


def _resp(body: bytes, content_type: str = "application/x-json-stream") -> httpx.Response:
    """Build a stand-alone Response with an attached request (for .text/.headers)."""
    return httpx.Response(
        200,
        content=body,
        headers={"content-type": content_type},
        request=httpx.Request("POST", "http://localhost:3552/api/environments/0/projects/p1/build"),
    )


# ── parser ────────────────────────────────────────────────────────────


def test_parses_normal_stream() -> None:
    """A normal action stream yields success, the activity id, every log and done."""
    result = parse_stream_response(_resp(STREAM))
    assert result["success"] is True
    assert result["activityId"] == "a1"
    assert result["logs"] == [
        "#1 [internal] load remote build context",
        "#1 CACHED",
        "",
    ]
    assert result["done"] is True


def test_first_activity_id_wins() -> None:
    """Only the first activityId encountered is kept; later events do not overwrite it."""
    body = b'{"activityId":"first","type":"activity"}\n{"activityId":"second","type":"activity"}\n{"log":"step"}\n'
    result = parse_stream_response(_resp(body))
    assert result["activityId"] == "first"
    assert "done" not in result


def test_done_only_when_true() -> None:
    """A stream without a true done record leaves the key absent."""
    result = parse_stream_response(_resp(b'{"log":"still running"}\n'))
    assert result["success"] is True
    assert "done" not in result


def test_non_json_line_is_tolerated() -> None:
    """A malformed line is appended to logs verbatim instead of raising."""
    body = b'{"log":"before"}\nthis is not json\n{"log":"after"}\n'
    result = parse_stream_response(_resp(body))
    assert result["success"] is True
    assert result["logs"] == ["before", "this is not json", "after"]


def test_error_event_marks_failure() -> None:
    """A truthy error key flips success to False and surfaces the error."""
    body = b'{"log":"step"}\n{"error":"compose build failed"}\n{"done":true}\n'
    result = parse_stream_response(_resp(body))
    assert result["success"] is False
    assert result["error"] == "compose build failed"
    assert result["logs"] == ["step"]


def test_empty_body() -> None:
    """An empty body parses to a successful result with no logs."""
    result = parse_stream_response(_resp(b""))
    assert result == {"success": True, "logs": []}


# ── tool call site ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_redeploy_project_parses_stream(mcp: Any, httpx_mock: Any) -> None:
    """redeploy_project returns the parsed stream, not a JSONDecodeError."""
    httpx_mock.add_response(
        url="http://localhost:3552/api/agents/0/projects/p1/deploy",
        method="POST",
        match_params={"action": "redeploy"},
        content=b'{"activityId":"a1","type":"activity"}\n{"log":"step"}\n{"done":true}\n',
        headers={"content-type": "application/x-json-stream"},
    )
    result = await call_tool(mcp, "redeploy_project", project_id="p1")
    assert result["success"] is True
    assert result["activityId"] == "a1"
    assert result["logs"] == ["step"]
    assert result["done"] is True
