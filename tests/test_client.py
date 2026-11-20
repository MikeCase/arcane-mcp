"""Tests for the client module."""

from __future__ import annotations

import pytest
from pytest_httpx import HTTPXMock

from arcane_mcp import client

VERSION_URL = "http://localhost:3552/api/version"


@pytest.fixture(autouse=True)
def isolated_client(monkeypatch: pytest.MonkeyPatch):
    """Reset the cached client and version cache around every test here."""
    monkeypatch.delenv("ARCANE_API_VERSION", raising=False)
    client._client = None
    client.reset_version_cache()
    yield
    client._client = None
    client.reset_version_cache()


def test_require_client_raises_without_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """require_client raises RuntimeError when env vars are missing."""
    monkeypatch.delenv("ARCANE_BASE_URL", raising=False)
    monkeypatch.delenv("ARCANE_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="ARCANE_BASE_URL and ARCANE_API_KEY must be set"):
        client.require_client()


def test_require_client_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """require_client returns a client when env vars are set."""
    c = client.require_client()
    assert c is not None


def test_build_headers_empty() -> None:
    """_build_headers returns empty dict when no agent_token."""
    result = client._build_headers()
    assert result == {}


def test_build_headers_with_token() -> None:
    """_build_headers returns agent token header."""
    result = client._build_headers(agent_token="tok_abc")
    assert result == {"X-Arcane-Agent-Token": "tok_abc"}


# ── version detection: env override ───────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("3", 3),
        ("v3.1.0", 3),
        ("2", 2),
        ("v2.17.1", 2),
    ],
)
async def test_detect_version_from_override(
    monkeypatch: pytest.MonkeyPatch,
    httpx_mock: HTTPXMock,
    value: str,
    expected: int,
) -> None:
    """ARCANE_API_VERSION wins and makes no HTTP call."""
    monkeypatch.setenv("ARCANE_API_VERSION", value)
    assert await client.detect_api_version() == expected
    assert httpx_mock.get_requests() == []


@pytest.mark.asyncio
async def test_override_is_not_cached(monkeypatch: pytest.MonkeyPatch, httpx_mock: HTTPXMock) -> None:
    """Removing the override falls back to detection on the next call."""
    monkeypatch.setenv("ARCANE_API_VERSION", "3")
    assert await client.detect_api_version() == 3
    monkeypatch.delenv("ARCANE_API_VERSION")
    httpx_mock.add_response(
        url=VERSION_URL,
        method="GET",
        json={"currentVersion": "v2.17.1"},
    )
    assert await client.detect_api_version() == 2


# ── version detection: /api/version ───────────────────────────────────


@pytest.mark.asyncio
async def test_detect_version_from_api(httpx_mock: HTTPXMock) -> None:
    """currentVersion is parsed from GET /api/version."""
    httpx_mock.add_response(
        url=VERSION_URL,
        method="GET",
        json={"currentVersion": "v3.1.0", "newestVersion": "v3.1.0", "updateAvailable": False},
    )
    assert await client.detect_api_version() == 3


@pytest.mark.asyncio
async def test_detected_version_is_cached(httpx_mock: HTTPXMock) -> None:
    """A successful detection is cached; only one HTTP call is made."""
    httpx_mock.add_response(
        url=VERSION_URL,
        method="GET",
        json={"currentVersion": "v2.17.1"},
    )
    assert await client.detect_api_version() == 2
    assert await client.detect_api_version() == 2
    assert len(httpx_mock.get_requests()) == 1


@pytest.mark.asyncio
async def test_detect_version_failure_falls_back_to_2(httpx_mock: HTTPXMock) -> None:
    """A non-200 from /api/version yields 2 instead of raising."""
    httpx_mock.add_response(
        url=VERSION_URL,
        method="GET",
        status_code=500,
        text="boom",
    )
    assert await client.detect_api_version() == 2


@pytest.mark.asyncio
async def test_detect_version_failure_is_not_cached(httpx_mock: HTTPXMock) -> None:
    """The fallback is retried on the next call, which can still find v3."""
    httpx_mock.add_response(
        url=VERSION_URL,
        method="GET",
        status_code=503,
        text="unavailable",
    )
    httpx_mock.add_response(
        url=VERSION_URL,
        method="GET",
        json={"currentVersion": "v3.0.0"},
    )
    assert await client.detect_api_version() == 2
    assert await client.detect_api_version() == 3
    assert len(httpx_mock.get_requests()) == 2


@pytest.mark.asyncio
async def test_detect_version_unparsable_body_falls_back(httpx_mock: HTTPXMock) -> None:
    """A body without a usable currentVersion yields 2."""
    httpx_mock.add_response(
        url=VERSION_URL,
        method="GET",
        json={"currentVersion": None},
    )
    assert await client.detect_api_version() == 2


# ── prefixes ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.asyncio
async def test_api_prefix_v3(monkeypatch: pytest.MonkeyPatch) -> None:
    """v3 uses the agents prefix (environments was renamed upstream)."""
    monkeypatch.setenv("ARCANE_API_VERSION", "3")
    assert await client.api_prefix("abc-123") == "/api/agents/abc-123"


@pytest.mark.asyncio
@pytest.mark.asyncio
async def test_collection_v3(monkeypatch: pytest.MonkeyPatch) -> None:
    """v3 uses the agents collection path (environments was renamed upstream)."""
    monkeypatch.setenv("ARCANE_API_VERSION", "3")
    assert await client.api_collection() == "/api/agents"


@pytest.mark.asyncio
async def test_collection_makes_no_request(monkeypatch: pytest.MonkeyPatch) -> None:
    """The collection path is static now — no version probe, no HTTP."""
    monkeypatch.delenv("ARCANE_API_VERSION", raising=False)
    assert await client.api_collection() == "/api/agents"
    assert await client.api_prefix("0") == "/api/agents/0"


@pytest.mark.asyncio
@pytest.mark.asyncio
async def test_env_path_joins_prefix(monkeypatch: pytest.MonkeyPatch) -> None:
    """env_path joins the agents prefix and suffix."""
    monkeypatch.setenv("ARCANE_API_VERSION", "3")
    assert await client.env_path("0", "/projects/p1") == "/api/agents/0/projects/p1"


@pytest.mark.asyncio
async def test_env_path_accepts_bare_suffix(monkeypatch: pytest.MonkeyPatch) -> None:
    """A suffix without a leading slash still joins cleanly."""
    monkeypatch.setenv("ARCANE_API_VERSION", "3")
    assert await client.env_path("0", "projects") == "/api/agents/0/projects"
