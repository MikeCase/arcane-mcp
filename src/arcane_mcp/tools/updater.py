"""Updater management tools."""
from __future__ import annotations

import logging
from typing import Any

import httpx
from fastmcp import FastMCP

from ..client import _build_headers, require_client
from ..safety import ToolClass, compute_operation_hash, get_token_store

logger = logging.getLogger(__name__)


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    async def run_updater(env_id: str = "0", agent_token: str | None = None) -> Any:
        """Run the updater to apply pending container updates. Requires confirmation via confirmation_token."""
        token = get_token_store().create(
            action="run_updater",
            target=env_id,
            endpoint=f"/api/environments/{env_id}/updater/run",
            method="POST",
            body=None,
            params=None,
            classification=ToolClass.DESTRUCTIVE_WRITE,
            env_id=env_id,
            agent_token=agent_token,
        )
        return {"warning": "Destructive operation. Call confirm_operation(token=...) to proceed.", "confirmation_token": token, "classification": ToolClass.DESTRUCTIVE_WRITE, "operation_hash": compute_operation_hash("run_updater", env_id, None, None), "target": env_id, "action": "run_updater"}

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
