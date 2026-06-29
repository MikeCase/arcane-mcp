"""Compose project management tools."""
from __future__ import annotations

import logging
from typing import Any

import httpx
from fastmcp import FastMCP

from ..client import _build_headers, require_client
from ..safety import get_token_store

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
    async def remove_project(project_id: str, env_id: str = "0", agent_token: str | None = None) -> Any:
        """Remove a Compose project."""
        token = get_token_store().create(
            action="remove_project",
            target=project_id,
            endpoint=f"/api/environments/{env_id}/projects/{project_id}",
            method="DELETE",
            body=None,
            params=None,
            env_id=env_id,
            agent_token=agent_token,
        )
        return {
            "warning": "Destructive operation. Call confirm_operation(token=...) to proceed.",
            "confirmation_token": token,
            "target": project_id,
            "action": "remove_project",
        }

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

    @mcp.tool()
    async def get_project_counts(env_id: str = "0", agent_token: str | None = None) -> Any:
        """Get counts of Compose projects in the given environment."""
        client = require_client()
        url = f"/api/environments/{env_id}/projects/counts"
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
    async def project_down(project_id: str, env_id: str = "0", agent_token: str | None = None) -> Any:
        """Take a Compose project down (stop and remove containers)."""
        token = get_token_store().create(
            action="project_down",
            target=project_id,
            endpoint=f"/api/environments/{env_id}/projects/{project_id}/down",
            method="POST",
            body=None,
            params=None,
            env_id=env_id,
            agent_token=agent_token,
        )
        return {
            "warning": "Destructive operation. Call confirm_operation(token=...) to proceed.",
            "confirmation_token": token,
            "target": project_id,
            "action": "project_down",
        }

    @mcp.tool()
    async def restart_project(project_id: str, env_id: str = "0", agent_token: str | None = None) -> Any:
        """Restart a Compose project."""
        token = get_token_store().create(
            action="restart_project",
            target=project_id,
            endpoint=f"/api/environments/{env_id}/projects/{project_id}/restart",
            method="POST",
            body=None,
            params=None,
            env_id=env_id,
            agent_token=agent_token,
        )
        return {
            "warning": "Destructive operation. Call confirm_operation(token=...) to proceed.",
            "confirmation_token": token,
            "target": project_id,
            "action": "restart_project",
        }

    @mcp.tool()
    async def build_project(project_id: str, env_id: str = "0", agent_token: str | None = None) -> Any:
        """Build a Compose project's images."""
        client = require_client()
        url = f"/api/environments/{env_id}/projects/{project_id}/build"
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
    async def archive_project(project_id: str, env_id: str = "0", agent_token: str | None = None) -> Any:
        """Archive a Compose project."""
        client = require_client()
        url = f"/api/environments/{env_id}/projects/{project_id}/archive"
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
    async def unarchive_project(project_id: str, env_id: str = "0", agent_token: str | None = None) -> Any:
        """Unarchive a Compose project."""
        client = require_client()
        url = f"/api/environments/{env_id}/projects/{project_id}/unarchive"
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
    async def pull_project_images(project_id: str, env_id: str = "0", agent_token: str | None = None) -> Any:
        """Pull images for a Compose project."""
        client = require_client()
        url = f"/api/environments/{env_id}/projects/{project_id}/pull"
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
    async def get_project_compose(project_id: str, env_id: str = "0", agent_token: str | None = None) -> Any:
        """Get the Compose file content for a project."""
        client = require_client()
        url = f"/api/environments/{env_id}/projects/{project_id}/compose"
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
    async def get_project_file(project_id: str, env_id: str = "0", agent_token: str | None = None) -> Any:
        """Get the project file content for a Compose project."""
        client = require_client()
        url = f"/api/environments/{env_id}/projects/{project_id}/file"
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
    async def update_project_services(project_id: str, env_id: str = "0", agent_token: str | None = None) -> Any:
        """Update services of a Compose project from the current compose config."""
        client = require_client()
        url = f"/api/environments/{env_id}/projects/{project_id}/update-services"
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
    async def get_project_runtime(project_id: str, env_id: str = "0", agent_token: str | None = None) -> Any:
        """Get the runtime info for a Compose project."""
        client = require_client()
        url = f"/api/environments/{env_id}/projects/{project_id}/runtime"
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
