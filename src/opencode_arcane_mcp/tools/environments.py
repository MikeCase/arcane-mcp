"""Environment management tools."""
from __future__ import annotations

import logging
from typing import Any

import httpx
from fastmcp import FastMCP

from ..client import require_client

logger = logging.getLogger(__name__)


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    async def list_environments() -> Any:
        """List all environments (local + remote agents)."""
        client = require_client()
        url = "/api/environments"
        try:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            logger.warning("HTTP %s on %s: %s", resp.status_code, url, resp.text)
            return {"error": str(e), "status_code": resp.status_code, "detail": resp.text}
        except Exception as e:
            logger.exception("Unexpected error on %s", url)
            return {"error": str(e)}

    @mcp.tool()
    async def get_environment(env_id: str) -> Any:
        """Get details of a specific environment."""
        client = require_client()
        url = f"/api/environments/{env_id}"
        try:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            logger.warning("HTTP %s on %s: %s", resp.status_code, url, resp.text)
            return {"error": str(e), "status_code": resp.status_code, "detail": resp.text}
        except Exception as e:
            logger.exception("Unexpected error on %s", url)
            return {"error": str(e)}

    @mcp.tool()
    async def create_environment(name: str, api_url: str, agent_token: str) -> Any:
        """Register a new remote agent environment."""
        client = require_client()
        url = "/api/environments"
        payload = {"name": name, "apiUrl": api_url, "accessToken": agent_token}
        try:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            logger.warning("HTTP %s on %s: %s", resp.status_code, url, resp.text)
            return {"error": str(e), "status_code": resp.status_code, "detail": resp.text}
        except Exception as e:
            logger.exception("Unexpected error on %s", url)
            return {"error": str(e)}

    @mcp.tool()
    async def update_environment(env_id: str, name: str | None = None, api_url: str | None = None, agent_token: str | None = None) -> Any:
        """Update environment settings (name, API URL, or access token)."""
        client = require_client()
        url = f"/api/environments/{env_id}"
        payload: dict[str, Any] = {}
        if name is not None:
            payload["name"] = name
        if api_url is not None:
            payload["apiUrl"] = api_url
        if agent_token is not None:
            payload["accessToken"] = agent_token
        try:
            resp = await client.put(url, json=payload)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            logger.warning("HTTP %s on %s: %s", resp.status_code, url, resp.text)
            return {"error": str(e), "status_code": resp.status_code, "detail": resp.text}
        except Exception as e:
            logger.exception("Unexpected error on %s", url)
            return {"error": str(e)}

    @mcp.tool()
    async def remove_environment(env_id: str, confirm: bool = False) -> Any:
        """Remove an environment. Requires confirm=True to execute."""
        if not confirm:
            return {"warning": "Destructive operation. Set confirm=True to remove this environment.", "env_id": env_id}
        client = require_client()
        url = f"/api/environments/{env_id}"
        try:
            resp = await client.delete(url)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            logger.warning("HTTP %s on %s: %s", resp.status_code, url, resp.text)
            return {"error": str(e), "status_code": resp.status_code, "detail": resp.text}
        except Exception as e:
            logger.exception("Unexpected error on %s", url)
            return {"error": str(e)}
