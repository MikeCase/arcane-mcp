"""Volume management tools."""
from __future__ import annotations

import logging
from typing import Any

import httpx
from fastmcp import FastMCP

from ..client import _build_headers, require_client

logger = logging.getLogger(__name__)


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    async def list_volumes(env_id: str = "0", agent_token: str | None = None) -> Any:
        """List all volumes in the given environment."""
        client = require_client()
        url = f"/api/environments/{env_id}/volumes"
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
    async def create_volume(
        name: str, driver: str = "local", labels: str | None = None,
        env_id: str = "0", agent_token: str | None = None,
    ) -> Any:
        """Create a new volume in the given environment."""
        client = require_client()
        url = f"/api/environments/{env_id}/volumes"
        body: dict[str, Any] = {"name": name, "driver": driver}
        if labels:
            body["labels"] = labels
        try:
            resp = await client.post(url, json=body, headers=_build_headers(agent_token))
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            logger.warning("HTTP %s on %s: %s", resp.status_code, url, resp.text)
            return {"error": str(e), "status_code": resp.status_code, "detail": resp.text}
        except Exception as e:
            logger.exception("Unexpected error on %s", url)
            return {"error": str(e)}

    @mcp.tool()
    async def inspect_volume(name: str, env_id: str = "0", agent_token: str | None = None) -> Any:
        """Inspect a volume by name."""
        client = require_client()
        url = f"/api/environments/{env_id}/volumes/{name}"
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
    async def remove_volume(
        name: str, force: bool = False, env_id: str = "0",
        agent_token: str | None = None, confirm: bool = False,
    ) -> Any:
        """Remove a volume by name. Destructive; requires confirm=True."""
        if not confirm:
            return {"warning": "Destructive operation requires confirm=True to proceed."}
        client = require_client()
        url = f"/api/environments/{env_id}/volumes/{name}"
        body = {"force": str(force).lower()}
        try:
            resp = await client.request("DELETE", url, json=body, headers=_build_headers(agent_token))
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            logger.warning("HTTP %s on %s: %s", resp.status_code, url, resp.text)
            return {"error": str(e), "status_code": resp.status_code, "detail": resp.text}
        except Exception as e:
            logger.exception("Unexpected error on %s", url)
            return {"error": str(e)}
