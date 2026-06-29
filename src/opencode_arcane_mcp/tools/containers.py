"""Container lifecycle tools."""
from __future__ import annotations

import logging
from typing import Any

import httpx
from fastmcp import FastMCP

from ..client import _build_headers, require_client

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
            return resp.json()
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
        agent_token: str | None = None, confirm: bool = False,
    ) -> Any:
        """Remove a container. Requires confirm=True to execute."""
        if not confirm:
            return {"warning": "Destructive operation. Set confirm=True to remove this container.", "container_id": container_id}
        client = require_client()
        url = f"/api/environments/{env_id}/containers/{container_id}"
        params = {"force": str(force).lower()}
        try:
            resp = await client.delete(url, params=params, headers=_build_headers(agent_token))
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            logger.warning("HTTP %s on %s: %s", resp.status_code, url, resp.text)
            return {"error": str(e), "status_code": resp.status_code, "detail": resp.text}
        except Exception as e:
            logger.exception("Unexpected error on %s", url)
            return {"error": str(e)}

    @mcp.tool()
    async def create_container(
        image: str, name: str, env_id: str = "0",
        agent_token: str | None = None, command: str | None = None,
        env: str | None = None, labels: str | None = None,
    ) -> Any:
        """Create and optionally start a container."""
        client = require_client()
        url = f"/api/environments/{env_id}/containers"
        payload: dict[str, Any] = {"image": image, "name": name}
        if command:
            payload["command"] = command
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
        """Execute a command inside a running container."""
        client = require_client()
        url = f"/api/environments/{env_id}/containers/{container_id}/exec"
        payload = {"command": command}
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
    async def get_container_logs(container_id: str, tail: int = 100, env_id: str = "0", agent_token: str | None = None) -> Any:
        """Fetch logs from a container."""
        client = require_client()
        url = f"/api/environments/{env_id}/containers/{container_id}/logs"
        params = {"tail": str(tail)}
        try:
            resp = await client.get(url, params=params, headers=_build_headers(agent_token))
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            logger.warning("HTTP %s on %s: %s", resp.status_code, url, resp.text)
            return {"error": str(e), "status_code": resp.status_code, "detail": resp.text}
        except Exception as e:
            logger.exception("Unexpected error on %s", url)
            return {"error": str(e)}

    @mcp.tool()
    async def get_container_stats(container_id: str, env_id: str = "0", agent_token: str | None = None) -> Any:
        """Get live resource usage stats for a container."""
        client = require_client()
        url = f"/api/environments/{env_id}/containers/{container_id}/stats"
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
