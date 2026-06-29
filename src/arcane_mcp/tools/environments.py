"""Environment management tools."""
from __future__ import annotations

import logging
from typing import Any

import httpx
from fastmcp import FastMCP

from ..client import require_client
from ..safety import get_token_store

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
    async def remove_environment(env_id: str) -> Any:
        """Remove an environment. Requires confirmation via confirmation_token."""
        token = get_token_store().create(
            action="remove_environment",
            target=env_id,
            endpoint=f"/api/environments/{env_id}",
            method="DELETE",
            body=None,
            params=None,
            env_id=env_id,
            agent_token=None,
        )
        return {"warning": "Destructive operation. Call confirm_operation(token=...) to proceed.", "confirmation_token": token, "target": env_id, "action": "remove_environment"}
