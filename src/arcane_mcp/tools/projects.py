"""Compose project management tools."""
from __future__ import annotations

import logging
import re
from typing import Any

import httpx
from fastmcp import FastMCP

from ..client import _build_headers, require_client
from ..safety import ToolClass, compute_operation_hash, get_token_store

logger = logging.getLogger(__name__)


def _parse_compose_plan(compose_content: str) -> dict:
    """Extract a basic plan/receipt from compose content without yaml parser."""
    plan = {"services": [], "images": []}
    current_service = None
    for line in compose_content.split('\n'):
        stripped = line.strip()
        if stripped.startswith('#') or not stripped:
            continue
        # Detect service definition (top-level key with colon, not indented)
        if not line.startswith(' ') and not line.startswith('\t') and stripped.endswith(':') and stripped not in ('services:', 'networks:', 'volumes:', 'configs:', 'secrets:'):
            current_service = stripped[:-1]
            plan["services"].append(current_service)
        elif 'image:' in stripped and current_service:
            img = stripped.split('image:')[1].strip().strip('"').strip("'")
            if img:
                plan["images"].append(img)
    return plan


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
        plan = _parse_compose_plan(compose_content)
        token = get_token_store().create(
            action="deploy_project",
            target=project_name,
            endpoint=f"/api/environments/{env_id}/projects",
            method="POST",
            body={"compose": compose_content, "name": project_name},
            params=None,
            classification=ToolClass.DESTRUCTIVE_WRITE,
            env_id=env_id,
            agent_token=agent_token,
        )
        op_hash = compute_operation_hash("deploy_project", project_name, {"compose": compose_content, "name": project_name}, None)
        return {
            "classification": ToolClass.DESTRUCTIVE_WRITE,
            "risk_level": "high",
            "warning": "Compose deployment is a high-risk operation. "
                       f"This will deploy project '{project_name}' with the resources listed below. "
                       "Verify the plan, then call confirm_operation() with the token.",
            "plan": plan,
            "confirmation_token": token,
            "operation_hash": op_hash,
            "target": project_name,
            "action": "deploy_project",
        }

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
            classification=ToolClass.DESTRUCTIVE_WRITE,
            env_id=env_id,
            agent_token=agent_token,
        )
        return {
            "warning": "Destructive operation. Call confirm_operation(token=...) to proceed.",
            "confirmation_token": token,
            "classification": ToolClass.DESTRUCTIVE_WRITE,
            "operation_hash": compute_operation_hash("remove_project", project_id, None, None),
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
        plan = {}
        if compose_content:
            plan = _parse_compose_plan(compose_content)
        token = get_token_store().create(
            action="update_project",
            target=project_id,
            endpoint=f"/api/environments/{env_id}/projects/{project_id}",
            method="PUT",
            body=payload,
            params=None,
            classification=ToolClass.DESTRUCTIVE_WRITE,
            env_id=env_id,
            agent_token=agent_token,
        )
        op_hash = compute_operation_hash("update_project", project_id, payload, None)
        return {
            "classification": ToolClass.DESTRUCTIVE_WRITE,
            "risk_level": "high",
            "warning": "Compose update is a high-risk operation. "
                       f"This will update project '{project_id}' and may mutate networks, volumes, "
                       "env, images, and restart policies. Verify the plan, then call confirm_operation() with the token.",
            "confirmation_token": token,
            "operation_hash": op_hash,
            "target": project_id,
            "action": "update_project",
            "plan": plan,
        }

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
            classification=ToolClass.DESTRUCTIVE_WRITE,
            env_id=env_id,
            agent_token=agent_token,
        )
        return {
            "warning": "Destructive operation. Call confirm_operation(token=...) to proceed.",
            "confirmation_token": token,
            "classification": ToolClass.DESTRUCTIVE_WRITE,
            "operation_hash": compute_operation_hash("project_down", project_id, None, None),
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
            classification=ToolClass.DESTRUCTIVE_WRITE,
            env_id=env_id,
            agent_token=agent_token,
        )
        return {
            "warning": "Destructive operation. Call confirm_operation(token=...) to proceed.",
            "confirmation_token": token,
            "classification": ToolClass.DESTRUCTIVE_WRITE,
            "operation_hash": compute_operation_hash("restart_project", project_id, None, None),
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
    async def get_project_file(project_id: str, env_id: str = "0", agent_token: str | None = None) -> Any:
        """Get the project file content for a Compose project."""
        client = require_client()
        url = f"/api/environments/{env_id}/projects/{project_id}/file"
        try:
            resp = await client.get(url, headers=_build_headers(agent_token))
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
