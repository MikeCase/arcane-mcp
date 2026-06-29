"""Compose project management tools."""
from __future__ import annotations

import logging
from typing import Any

import httpx
from fastmcp import FastMCP

from ..client import _build_headers, require_client

logger = logging.getLogger(__name__)


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    async def list_projects(env_id: str = "0", agent_token: str | None = None) -> Any:
        """List all Compose projects in the given environment."""
        client = require_client()
        url = f"/api/environments/{env_id}/projects"
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
    async def get_project(project_id: str, env_id: str = "0", agent_token: str | None = None) -> Any:
        """Get details of a specific Compose project."""
        client = require_client()
        url = f"/api/environments/{env_id}/projects/{project_id}"
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
    async def deploy_project(compose_content: str, project_name: str, env_id: str = "0", agent_token: str | None = None) -> Any:
        """Deploy a new Compose project from compose content."""
        client = require_client()
        url = f"/api/environments/{env_id}/projects"
        payload = {"compose": compose_content, "name": project_name}
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

    @mcp.tool()
    async def redeploy_project(project_id: str, env_id: str = "0", agent_token: str | None = None) -> Any:
        """Redeploy a Compose project."""
        client = require_client()
        url = f"/api/environments/{env_id}/projects/{project_id}/redeploy"
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
    async def remove_project(project_id: str, env_id: str = "0", agent_token: str | None = None, confirm: bool = False) -> Any:
        """Remove a Compose project. Requires confirm=True to execute."""
        if not confirm:
            return {"warning": "Destructive operation. Set confirm=True to remove this project.", "project_id": project_id}
        client = require_client()
        url = f"/api/environments/{env_id}/projects/{project_id}"
        try:
            resp = await client.delete(url, headers=_build_headers(agent_token))
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            logger.warning("HTTP %s on %s: %s", resp.status_code, url, resp.text)
            return {"error": str(e), "status_code": resp.status_code, "detail": resp.text}
        except Exception as e:
            logger.exception("Unexpected error on %s", url)
            return {"error": str(e)}

    @mcp.tool()
    async def update_project(
        project_id: str, env_id: str = "0",
        agent_token: str | None = None, compose_content: str | None = None,
        project_name: str | None = None,
    ) -> Any:
        """Update a Compose project's configuration."""
        payload: dict = {}
        if compose_content is not None:
            payload["compose"] = compose_content
        if project_name is not None:
            payload["name"] = project_name
        if not payload:
            return {"warning": "No update payload provided. Pass compose_content or project_name to update."}
        client = require_client()
        url = f"/api/environments/{env_id}/projects/{project_id}"
        try:
            resp = await client.put(url, json=payload, headers=_build_headers(agent_token))
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            logger.warning("HTTP %s on %s: %s", resp.status_code, url, resp.text)
            return {"error": str(e), "status_code": resp.status_code, "detail": resp.text}
        except Exception as e:
            logger.exception("Unexpected error on %s", url)
            return {"error": str(e)}
