"""Environment (agent) management tools.

Arcane v3 calls these "agents": the collection moved from the v2 environments
path to ``/api/agents`` (upstream PR #4731), v3 serves no v2 alias, and 1.0.0 of
this server dropped v2 entirely.  Tool names keep the word "environment" for
public API stability; the docstrings say "agent" so a model knows what it is
actually listing.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx
from fastmcp import FastMCP

from ..client import api_collection, env_path, paginate_all, require_client
from ..safety import ToolClass, compute_operation_hash, get_token_store

logger = logging.getLogger(__name__)


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    async def list_environments() -> Any:
        """List all environments (agents): the local agent plus every remote agent (every page)."""
        url = await api_collection()
        try:
            return await paginate_all(url)
        except httpx.HTTPStatusError as e:
            logger.warning("HTTP %s on %s: %s", e.response.status_code, url, e.response.text)
            return {"error": str(e), "status_code": e.response.status_code, "detail": e.response.text}
        except Exception as e:
            logger.exception("Unexpected error on %s", url)
            return {"error": str(e)}

    @mcp.tool()
    async def get_environment(env_id: str) -> Any:
        """Get details of one environment (agent) by ID."""
        client = require_client()
        url = await env_path(env_id, "")
        try:
            resp = await client.get(url)
            resp.raise_for_status()
            result = resp.json()
            return {
                "classification": ToolClass.CREDENTIAL_SENSITIVE,
                "warning": "This response may contain sensitive data (env vars, secrets, config). Handle with care.",
                "data": result,
            }
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
        url = await api_collection()
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
        """Update agent settings (name, API URL, or access token). v3 uses PATCH."""
        client = require_client()
        url = await env_path(env_id, "")
        payload: dict[str, Any] = {}
        if name is not None:
            payload["name"] = name
        if api_url is not None:
            payload["apiUrl"] = api_url
        if agent_token is not None:
            payload["accessToken"] = agent_token
        try:
            resp = await client.patch(url, json=payload)
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
        """Remove an environment (agent). Requires confirmation via confirmation_token."""
        token = get_token_store().create(
            action="remove_environment",
            target=env_id,
            endpoint=await env_path(env_id, ""),
            method="DELETE",
            body=None,
            params=None,
            classification=ToolClass.DESTRUCTIVE_WRITE,
            env_id=env_id,
            agent_token=None,
        )
        return {
            "warning": "Destructive operation. Call confirm_operation(token=...) to proceed.",
            "confirmation_token": token,
            "classification": ToolClass.DESTRUCTIVE_WRITE,
            "operation_hash": compute_operation_hash("remove_environment", env_id, None, None),
            "target": env_id,
            "action": "remove_environment",
        }
