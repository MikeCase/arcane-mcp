"""HTTP client helpers for Arcane API.

Arcane v3.0.0 renamed the multi-tenant environment routes from
``/api/environments/{env_id}`` to ``/api/agents/{env_id}`` (upstream PR
#4731); v3 serves no ``/api/environments`` alias at all.  The project and
resource payloads stayed the same, only the path prefix — and, for project
updates, ``PUT`` became ``PATCH``.

So the base path has to be resolved at runtime instead of hardcoded.  The
server version is read once per process from ``GET /api/version`` (present on
both majors) and cached; ``ARCANE_API_VERSION`` overrides that lookup for
tests and for pinning a deployment.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re

import httpx
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

load_dotenv()

_client: httpx.AsyncClient | None = None

# ── API version detection ──
# Cached major version of the Arcane server, plus the base URL it was
# detected against so a changed ARCANE_BASE_URL invalidates it.
_version_major: int | None = None
_version_base_url: str | None = None
_version_lock: asyncio.Lock | None = None


def get_client() -> httpx.AsyncClient | None:
    """Return a lazily-created AsyncClient for Arcane API, or None if not configured."""
    global _client
    if _client is None:
        base = os.environ.get("ARCANE_BASE_URL")
        key = os.environ.get("ARCANE_API_KEY")
        if not base or not key:
            logger.warning("Arcane client not configured: ARCANE_BASE_URL or ARCANE_API_KEY missing")
            return None
        _client = httpx.AsyncClient(
            base_url=base.rstrip("/"),
            headers={"X-Api-Key": key},
        )
        logger.info("Arcane client created for %s", base)
    return _client


def require_client() -> httpx.AsyncClient:
    client = get_client()
    if client is None:
        raise RuntimeError("ARCANE_BASE_URL and ARCANE_API_KEY must be set (and loaded) to use MCP tools.")
    return client


def _build_headers(agent_token: str | None = None) -> dict[str, str]:
    """Add X-Arcane-Agent-Token header if provided."""
    headers: dict[str, str] = {}
    if agent_token:
        headers["X-Arcane-Agent-Token"] = agent_token
    return headers


def _parse_major(value: str) -> int | None:
    """Parse a major version from ``2``, ``v2.17.1``, ``v3.1.0`` (or an int)."""
    match = re.match(r"^v?(\d+)", str(value).strip(), re.IGNORECASE)
    if match is None:
        return None
    return int(match.group(1))


def _get_version_lock() -> asyncio.Lock:
    """Lazily create the detection lock (safe outside a running loop)."""
    global _version_lock
    if _version_lock is None:
        _version_lock = asyncio.Lock()
    return _version_lock


def reset_version_cache() -> None:
    """Forget the cached API major version (used by tests, and on base URL change)."""
    global _version_major, _version_base_url
    _version_major = None
    _version_base_url = None


async def detect_api_version() -> int:
    """Return the Arcane major version (2 or 3) of the configured server.

    Resolution order:

    1. ``ARCANE_API_VERSION`` (``"2"``, ``"3"``, ``"v2.17.1"``, ``"v3.1.0"``) —
       no HTTP call is made and nothing is cached.
    2. A cached value from a previous call against the same base URL.
    3. ``GET /api/version`` -> ``currentVersion``.

    Detection never raises: a network error, a non-200 response or an
    unparsable body logs a warning and falls back to v2.  The fallback is not
    cached, so the next call retries and can still discover v3.
    """
    global _version_major, _version_base_url

    override = os.environ.get("ARCANE_API_VERSION")
    if override:
        parsed = _parse_major(override)
        if parsed is not None:
            return parsed
        logger.warning("Ignoring unparsable ARCANE_API_VERSION=%r", override)

    base_url = os.environ.get("ARCANE_BASE_URL")
    if _version_major is not None and _version_base_url == base_url:
        return _version_major

    async with _get_version_lock():
        # Re-check: another waiter may have populated the cache.
        if _version_major is not None and _version_base_url == base_url:
            return _version_major

        try:
            client = require_client()
            resp = await client.get("/api/version")
            resp.raise_for_status()
            current = resp.json().get("currentVersion")
            major = _parse_major(current) if current is not None else None
            if major is None:
                raise ValueError(f"no parsable currentVersion in /api/version response: {resp.text[:200]!r}")
        except Exception as e:
            logger.warning("Could not detect Arcane API version (%s); assuming v2", e)
            return 2

        _version_major = major
        _version_base_url = base_url
        logger.info("Detected Arcane API major version %s from %s", major, base_url)
        return major


async def api_prefix(env_id: str) -> str:
    """Return the multi-tenant base path for *env_id* on the detected server.

    ``/api/agents/{env_id}`` on v3+, ``/api/environments/{env_id}`` on v2.
    """
    major = await detect_api_version()
    if major >= 3:
        return f"/api/agents/{env_id}"
    return f"/api/environments/{env_id}"


async def api_collection() -> str:
    """Return the environment-collection base path on the detected server.

    ``/api/agents`` on v3+, ``/api/environments`` on v2.  Unlike
    :func:`api_prefix`, this path carries no ``env_id`` — it is the collection
    itself, which the environments tools (list/create/get/update/remove) manage.
    """
    major = await detect_api_version()
    if major >= 3:
        return "/api/agents"
    return "/api/environments"


async def env_path(env_id: str, suffix: str) -> str:
    """Return ``api_prefix(env_id) + suffix`` (e.g. ``env_path("0", "/projects")``)."""
    prefix = await api_prefix(env_id)
    if not suffix:
        return prefix
    if not suffix.startswith("/"):
        suffix = "/" + suffix
    return prefix + suffix
