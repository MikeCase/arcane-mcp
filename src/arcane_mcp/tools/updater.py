"""Updater management tools."""
from __future__ import annotations

import logging
from typing import Any

import httpx
from fastmcp import FastMCP

from ..client import _build_headers, require_client

logger = logging.getLogger(__name__)


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    async def run_updater(env_id: str = "0", agent_token: str | None = None, confirm: bool = False) -> Any:
        """Run the updater to apply pending container updates. Requires confirm=True."""
        if not confirm:
            return {"warning": "Destructive operation. Set confirm=True to run the updater."}
        client = require_client()
        url = f"/api/environments/{env_id}/updater/run"
        try:
            resp = await client.post(url, headers=_build_headers(agent_token))
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            logger.warning("HTTP %s on %s: %s", resp.status_code, url, resp.text)
            return {"error": str(e), "status_code": resp.status_code, "detail": resp.text}
        except Exception as e:
            logger.exception("Unexpected error on %s", url)
            return {"error": str(e)}

    @mcp.tool()
    async def get_updater_status(env_id: str = "0", agent_token: str | None = None) -> Any:
        """Get the current updater status."""
        client = require_client()
        url = f"/api/environments/{env_id}/updater/status"
        try:
            resp = await client.get(url, headers=_build_headers(agent_token))
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            logger.warning("HTTP %s on %s: %s", resp.status_code, url, resp.text)
            return {"error": str(e), "status_code": resp.status_code, "detail": resp.text}
        except Exception as e:
            logger.exception("Unexpected error on %s", url)
            return {"error": str(e)}

    @mcp.tool()
    async def get_updater_history(env_id: str = "0", agent_token: str | None = None) -> Any:
        """Get updater operation history."""
        client = require_client()
        url = f"/api/environments/{env_id}/updater/history"
        try:
            resp = await client.get(url, headers=_build_headers(agent_token))
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            logger.warning("HTTP %s on %s: %s", resp.status_code, url, resp.text)
            return {"error": str(e), "status_code": resp.status_code, "detail": resp.text}
        except Exception as e:
            logger.exception("Unexpected error on %s", url)
            return {"error": str(e)}
