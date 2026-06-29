"""System-level tools."""
from __future__ import annotations

import logging
from typing import Any

import httpx
from fastmcp import FastMCP

from ..client import _build_headers, require_client

logger = logging.getLogger(__name__)


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    async def get_docker_info(env_id: str = "0", agent_token: str | None = None) -> Any:
        """Get Docker system information for the given environment."""
        client = require_client()
        url = f"/api/environments/{env_id}/info"
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
    async def get_docker_version(env_id: str = "0", agent_token: str | None = None) -> Any:
        """Get Docker version for the given environment."""
        client = require_client()
        url = f"/api/environments/{env_id}/version"
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
    async def prune_system(volumes: bool = False, env_id: str = "0", agent_token: str | None = None, confirm: bool = False) -> Any:
        """Prune system resources for the given environment. Volumes prune is controlled by volumes flag."""
        if not confirm:
            return {"warning": "Destructive operation. Set confirm=True to prune system resources.", "volumes": volumes}
        client = require_client()
        url = f"/api/environments/{env_id}/prune"
        payload = {"volumes": str(volumes).lower()}
        try:
            resp = await client.post(url, json=payload, headers=_build_headers(agent_token))
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            logger.warning("HTTP %s on %s: %s", resp.status_code, url, resp.text)
            return {"error": str(e), "status_code": resp.status_code, "detail": resp.text}
        except Exception as e:
            logger.exception("Unexpected error on %s", url)
            return {"error": str(e)}
