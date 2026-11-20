"""Compose project management tools.

Targets Arcane v3+ only.  v3 moved project *actions* off their own sub-paths and
onto a query parameter — ``POST /projects/{projectId}?action=down`` — and gave
up/redeploy/pull a single endpoint, ``POST /projects/{projectId}/deploy``, whose
``action`` query parameter picks the operation and whose JSON body is a
``ProjectDeployOptions``.  Project update is ``PATCH``, teardown is a plain
``DELETE /projects/{projectId}``.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx
from fastmcp import FastMCP

from ..client import _build_headers, env_path, paginate_all, parse_stream_response, require_client
from ..safety import ToolClass, compute_operation_hash, get_token_store

logger = logging.getLogger(__name__)

_DEFAULT_WARNING = "Destructive operation. Call confirm_operation(token=...) to proceed."


def _propose_operation(
    *,
    action: str,
    target: str,
    endpoint: str,
    env_id: str,
    agent_token: str | None,
    method: str = "POST",
    body: dict[str, Any] | None = None,
    params: dict[str, Any] | None = None,
    warning: str = _DEFAULT_WARNING,
) -> dict[str, Any]:
    """Create a confirmation token for an operation and return the proposal.

    ``endpoint`` is already fully resolved by the caller (``env_path``), so the
    token carries the exact path and the query parameters that were proposed —
    ``confirm_operation()`` replays both verbatim.
    """
    token = get_token_store().create(
        action=action,
        target=target,
        endpoint=endpoint,
        method=method,
        body=body,
        params=params,
        classification=ToolClass.DESTRUCTIVE_WRITE,
        env_id=env_id,
        agent_token=agent_token,
    )
    return {
        "warning": warning,
        "confirmation_token": token,
        "classification": ToolClass.DESTRUCTIVE_WRITE,
        "operation_hash": compute_operation_hash(action, target, body, params),
        "target": target,
        "action": action,
    }


def _parse_compose_plan(compose_content: str) -> dict:
    """Extract a basic plan/receipt from compose content without yaml parser."""
    plan = {"services": [], "images": []}
    current_service = None
    for line in compose_content.split("\n"):
        stripped = line.strip()
        if stripped.startswith("#") or not stripped:
            continue
        # Detect service definition (top-level key with colon, not indented)
        if (
            not line.startswith(" ")
            and not line.startswith("\t")
            and stripped.endswith(":")
            and stripped not in ("services:", "networks:", "volumes:", "configs:", "secrets:")
        ):
            current_service = stripped[:-1]
            plan["services"].append(current_service)
        elif "image:" in stripped and current_service:
            img = stripped.split("image:")[1].strip().strip('"').strip("'")
            if img:
                plan["images"].append(img)
    return plan


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    async def list_projects(env_id: str = "0", agent_token: str | None = None) -> Any:
        """List all Compose projects in the given environment."""
        url = await env_path(env_id, "/projects")
        try:
            return await paginate_all(url, agent_token=agent_token)
        except httpx.HTTPStatusError as e:
            logger.warning("HTTP %s on %s: %s", e.response.status_code, url, e.response.text)
            return {"error": str(e), "status_code": e.response.status_code, "detail": e.response.text}
        except Exception as e:
            logger.exception("Unexpected error on %s", url)
            return {"error": str(e)}

    @mcp.tool()
    async def get_project(project_id: str, env_id: str = "0", agent_token: str | None = None) -> Any:
        """Get details of a specific Compose project."""
        client = require_client()
        url = await env_path(env_id, f"/projects/{project_id}")
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
        body = {
            "project": json.dumps(
                {"name": project_name, "composeContent": compose_content},
                sort_keys=True,
            ),
            "manifest": json.dumps({"fileChanges": []}, sort_keys=True),
        }
        token = get_token_store().create(
            action="deploy_project",
            target=project_name,
            endpoint=await env_path(env_id, "/projects"),
            method="POST",
            body=body,
            params=None,
            classification=ToolClass.DESTRUCTIVE_WRITE,
            env_id=env_id,
            agent_token=agent_token,
            encoding="multipart",
        )
        op_hash = compute_operation_hash("deploy_project", project_name, body, None)
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
        url = await env_path(env_id, f"/projects/{project_id}/deploy")
        try:
            # build=true: a "redeploy" that skips the build would serve a stale
            # image, which is what the upstream GitOps sync avoids too.
            resp = await client.post(
                url,
                headers=_build_headers(agent_token),
                params={"action": "redeploy"},
                json={"build": True},
            )
            resp.raise_for_status()
            return parse_stream_response(resp)
        except httpx.HTTPStatusError as e:
            logger.warning("HTTP %s on %s: %s", resp.status_code, url, resp.text)
            return {"error": str(e), "status_code": resp.status_code, "detail": resp.text}
        except Exception as e:
            logger.exception("Unexpected error on %s", url)
            return {"error": str(e)}

    @mcp.tool()
    async def remove_project(project_id: str, env_id: str = "0", agent_token: str | None = None) -> Any:
        """Remove a Compose project."""
        return _propose_operation(
            action="remove_project",
            target=project_id,
            endpoint=await env_path(env_id, f"/projects/{project_id}"),
            method="DELETE",
            env_id=env_id,
            agent_token=agent_token,
        )

    @mcp.tool()
    async def update_project(
        project_id: str,
        env_id: str = "0",
        agent_token: str | None = None,
        compose_content: str | None = None,
        project_name: str | None = None,
    ) -> Any:
        """Update a Compose project's configuration."""
        payload: dict = {}
        if compose_content is not None:
            payload["composeContent"] = compose_content
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
            endpoint=await env_path(env_id, f"/projects/{project_id}"),
            method="PATCH",
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
        url = await env_path(env_id, "/projects/counts")
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
        return _propose_operation(
            action="project_down",
            target=project_id,
            endpoint=await env_path(env_id, f"/projects/{project_id}"),
            params={"action": "down"},
            env_id=env_id,
            agent_token=agent_token,
        )

    @mcp.tool()
    async def restart_project(project_id: str, env_id: str = "0", agent_token: str | None = None) -> Any:
        """Restart a Compose project."""
        # An empty services list (i.e. no ``services`` query parameter) targets
        # every service in the project.
        return _propose_operation(
            action="restart_project",
            target=project_id,
            endpoint=await env_path(env_id, f"/projects/{project_id}"),
            params={"action": "restart"},
            env_id=env_id,
            agent_token=agent_token,
        )

    @mcp.tool()
    async def build_project(project_id: str, env_id: str = "0", agent_token: str | None = None) -> Any:
        """Build a Compose project's images."""
        client = require_client()
        url = await env_path(env_id, f"/projects/{project_id}/build")
        try:
            resp = await client.post(url, headers=_build_headers(agent_token))
            resp.raise_for_status()
            return parse_stream_response(resp)
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
        url = await env_path(env_id, f"/projects/{project_id}")
        try:
            resp = await client.post(
                url,
                headers=_build_headers(agent_token),
                params={"action": "archive"},
            )
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
        url = await env_path(env_id, f"/projects/{project_id}")
        try:
            resp = await client.post(
                url,
                headers=_build_headers(agent_token),
                params={"action": "unarchive"},
            )
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
        url = await env_path(env_id, f"/projects/{project_id}/deploy")
        try:
            # Empty ProjectDeployOptions: the ``pull`` action is itself the
            # instruction to pull, so leave the policy to the server/project
            # rather than forcing ``"always"`` over a policy the user chose.
            resp = await client.post(
                url,
                headers=_build_headers(agent_token),
                params={"action": "pull"},
                json={},
            )
            resp.raise_for_status()
            return parse_stream_response(resp)
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
        url = await env_path(env_id, f"/projects/{project_id}/compose")
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
        url = await env_path(env_id, f"/projects/{project_id}/workspace/file")
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
        # No ``services`` query parameter: the action targets every service.
        client = require_client()
        url = await env_path(env_id, f"/projects/{project_id}")
        try:
            resp = await client.post(
                url,
                headers=_build_headers(agent_token),
                params={"action": "updateservices"},
            )
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
        url = await env_path(env_id, f"/projects/{project_id}/runtime")
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
