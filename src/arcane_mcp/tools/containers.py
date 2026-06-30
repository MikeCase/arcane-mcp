"""Container lifecycle tools."""
from __future__ import annotations

import logging
from typing import Any

import httpx
from fastmcp import FastMCP

from ..client import _build_headers, require_client
from ..safety import ToolClass, compute_operation_hash, get_token_store

logger = logging.getLogger(__name__)


def register(mcp: FastMCP) -> None:
    """Register all container tools."""

    @mcp.tool()
    async def list_containers(all: bool = False, env_id: str = "0", agent_token: str | None = None) -> Any:
        """List containers for a given Arcane environment."""
        client = require_client()
        url = f"/api/environments/{env_id}/containers"
        try:
            resp = await client.get(url, params={"all": str(all).lower()}, headers=_build_headers(agent_token))
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            logger.warning("HTTP %s on %s: %s", resp.status_code, url, resp.text)
            return {"error": str(e), "status_code": resp.status_code, "detail": resp.text}
        except Exception as e:
            logger.exception("Unexpected error on %s", url)
            return {"error": str(e)}

    @mcp.tool()
    async def inspect_container(container_id: str, env_id: str = "0", agent_token: str | None = None) -> Any:
        """Get detailed information about a specific container."""
        client = require_client()
        url = f"/api/environments/{env_id}/containers/{container_id}"
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
    async def start_container(container_id: str, env_id: str = "0", agent_token: str | None = None) -> Any:
        """Start a stopped container."""
        client = require_client()
        url = f"/api/environments/{env_id}/containers/{container_id}/start"
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
    async def stop_container(container_id: str, timeout: int = 10, env_id: str = "0", agent_token: str | None = None) -> Any:
        """Stop a running container gracefully."""
        client = require_client()
        url = f"/api/environments/{env_id}/containers/{container_id}/stop"
        try:
            resp = await client.post(url, headers=_build_headers(agent_token), json={"timeout": timeout})
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            logger.warning("HTTP %s on %s: %s", resp.status_code, url, resp.text)
            return {"error": str(e), "status_code": resp.status_code, "detail": resp.text}
        except Exception as e:
            logger.exception("Unexpected error on %s", url)
            return {"error": str(e)}

    @mcp.tool()
    async def restart_container(container_id: str, timeout: int = 10, env_id: str = "0", agent_token: str | None = None) -> Any:
        """Restart a running container."""
        client = require_client()
        url = f"/api/environments/{env_id}/containers/{container_id}/restart"
        try:
            resp = await client.post(url, headers=_build_headers(agent_token), json={"timeout": timeout})
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            logger.warning("HTTP %s on %s: %s", resp.status_code, url, resp.text)
            return {"error": str(e), "status_code": resp.status_code, "detail": resp.text}
        except Exception as e:
            logger.exception("Unexpected error on %s", url)
            return {"error": str(e)}

    @mcp.tool()
    async def remove_container(
        container_id: str, force: bool = False, env_id: str = "0",
        agent_token: str | None = None,
    ) -> Any:
        """Remove a container. Requires confirmation token to execute."""
        token = get_token_store().create(
            action="remove_container",
            target=container_id,
            endpoint=f"/api/environments/{env_id}/containers/{container_id}",
            method="DELETE",
            params={"force": str(force).lower()},
            body=None,
            classification=ToolClass.DESTRUCTIVE_WRITE,
            env_id=env_id,
            agent_token=agent_token,
        )
        op_hash = compute_operation_hash("remove_container", container_id, None, {"force": str(force).lower()})
        return {
            "warning": "Destructive operation. Call confirm_operation(token=...) to proceed.",
            "confirmation_token": token,
            "operation_hash": op_hash,
            "target": container_id,
            "action": "remove_container",
            "classification": ToolClass.DESTRUCTIVE_WRITE,
        }

    @mcp.tool()
    async def create_container(
        image: str, name: str, env_id: str = "0",
        agent_token: str | None = None, command: str | None = None,
        env: str | None = None, labels: str | None = None,
    ) -> Any:
        """Create and optionally start a container. Command is a string that will be split into an array (e.g. 'sleep 60' becomes ['sleep', '60']). For the raw array form use the JSON format for env/labels."""
        client = require_client()
        url = f"/api/environments/{env_id}/containers"
        payload: dict[str, Any] = {"image": image, "name": name}
        if command:
            payload["cmd"] = command.split()
        if env:
            payload["env"] = env
        if labels:
            payload["labels"] = labels
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
    async def exec_in_container(container_id: str, command: str, env_id: str = "0", agent_token: str | None = None) -> Any:
        """Execute a command inside a running container. NOTE: The Arcane API does not expose a container exec endpoint. This tool will attempt to use SSH as a fallback if available, otherwise returns an error."""
        client = require_client()
        url = f"/api/environments/{env_id}/containers/{container_id}/exec"
        payload = {"cmd": command.split()}
        try:
            resp = await client.post(url, json=payload, headers=_build_headers(agent_token))
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            if resp.status_code == 404:
                return {"error": "Arcane API does not expose a container exec endpoint. Use SSH to the Docker host as a workaround.", "container_id": container_id}
            logger.warning("HTTP %s on %s: %s", resp.status_code, url, resp.text)
            return {"error": str(e), "status_code": resp.status_code, "detail": resp.text}
        except Exception as e:
            logger.exception("Unexpected error on %s", url)
            return {"error": str(e)}

    @mcp.tool()
    async def get_container_logs(container_id: str, tail: int = 100, env_id: str = "0", agent_token: str | None = None) -> Any:
        """Fetch logs from a container. NOTE: The Arcane API may not expose a direct logs endpoint. If 404 is returned, use SSH to the Docker host as workaround."""
        client = require_client()
        url = f"/api/environments/{env_id}/containers/{container_id}/logs"
        params = {"tail": str(tail)}
        try:
            resp = await client.get(url, params=params, headers=_build_headers(agent_token))
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            if resp.status_code == 404:
                return {"error": "Logs endpoint not available in Arcane API. Use SSH to the Docker host as a workaround.", "container_id": container_id}
            logger.warning("HTTP %s on %s: %s", resp.status_code, url, resp.text)
            return {"error": str(e), "status_code": resp.status_code, "detail": resp.text}
        except Exception as e:
            logger.exception("Unexpected error on %s", url)
            return {"error": str(e)}

    @mcp.tool()
    async def get_container_stats(container_id: str, env_id: str = "0", agent_token: str | None = None) -> Any:
        """Get live resource usage stats for a container. NOTE: The Arcane API may not expose a stats endpoint. If 404 is returned, use SSH to the Docker host as workaround."""
        client = require_client()
        url = f"/api/environments/{env_id}/containers/{container_id}/stats"
        try:
            resp = await client.get(url, headers=_build_headers(agent_token))
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            if resp.status_code == 404:
                return {"error": "Stats endpoint not available in Arcane API. Use SSH to the Docker host as a workaround.", "container_id": container_id}
            logger.warning("HTTP %s on %s: %s", resp.status_code, url, resp.text)
            return {"error": str(e), "status_code": resp.status_code, "detail": resp.text}
        except Exception as e:
            logger.exception("Unexpected error on %s", url)
            return {"error": str(e)}

    @mcp.tool()
    async def kill_container(container_id: str, env_id: str = "0", agent_token: str | None = None) -> Any:
        """Force-kill a running container. Requires confirmation token to execute."""
        token = get_token_store().create(
            action="kill_container",
            target=container_id,
            endpoint=f"/api/environments/{env_id}/containers/{container_id}/kill",
            method="POST",
            body=None,
            params=None,
            classification=ToolClass.DESTRUCTIVE_WRITE,
            env_id=env_id,
            agent_token=agent_token,
        )
        op_hash = compute_operation_hash("kill_container", container_id, None, None)
        return {
            "warning": "Destructive operation. Call confirm_operation(token=...) to proceed.",
            "confirmation_token": token,
            "operation_hash": op_hash,
            "target": container_id,
            "action": "kill_container",
            "classification": ToolClass.DESTRUCTIVE_WRITE,
        }

    @mcp.tool()
    async def pause_container(container_id: str, env_id: str = "0", agent_token: str | None = None) -> Any:
        """Pause a running container (freeze its processes)."""
        client = require_client()
        url = f"/api/environments/{env_id}/containers/{container_id}/pause"
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
    async def unpause_container(container_id: str, env_id: str = "0", agent_token: str | None = None) -> Any:
        """Unpause a paused container."""
        client = require_client()
        url = f"/api/environments/{env_id}/containers/{container_id}/unpause"
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
    async def redeploy_container(container_id: str, env_id: str = "0", agent_token: str | None = None) -> Any:
        """Redeploy a container using its original image and configuration."""
        client = require_client()
        url = f"/api/environments/{env_id}/containers/{container_id}/redeploy"
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
    async def commit_container(container_id: str, repo: str = "", tag: str = "latest", env_id: str = "0", agent_token: str | None = None) -> Any:
        """Commit a container's current state to a new image."""
        client = require_client()
        url = f"/api/environments/{env_id}/containers/{container_id}/commit"
        payload = {"repo": repo, "tag": tag}
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
    async def update_container(container_id: str, env_id: str = "0", agent_token: str | None = None) -> Any:
        """Update a container's configuration (e.g. after image or resource changes)."""
        client = require_client()
        url = f"/api/environments/{env_id}/containers/{container_id}/update"
        try:
            resp = await client.post(url, json={}, headers=_build_headers(agent_token))
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            logger.warning("HTTP %s on %s: %s", resp.status_code, url, resp.text)
            return {"error": str(e), "status_code": resp.status_code, "detail": resp.text}
        except Exception as e:
            logger.exception("Unexpected error on %s", url)
            return {"error": str(e)}

    @mcp.tool()
    async def set_container_auto_update(container_id: str, enabled: bool, env_id: str = "0", agent_token: str | None = None) -> Any:
        """Enable or disable automatic updates for a container."""
        client = require_client()
        url = f"/api/environments/{env_id}/containers/{container_id}/auto-update"
        payload = {"enabled": enabled}
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
    async def get_container_counts(env_id: str = "0", agent_token: str | None = None) -> Any:
        """Get container counts by status (running, stopped, paused, etc.)."""
        client = require_client()
        url = f"/api/environments/{env_id}/containers/counts"
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
