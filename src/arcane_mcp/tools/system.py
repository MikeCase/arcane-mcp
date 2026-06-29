"""System-level tools."""
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
    async def get_docker_info(env_id: str = "0", agent_token: str | None = None) -> Any:
        """Get Docker system information for the given environment."""
        client = require_client()
        url = f"/api/environments/{env_id}/system/docker/info"
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
    async def prune_system(
        containers: bool = True,
        images: bool = True,
        volumes: bool = False,
        networks: bool = True,
        build_cache: bool = False,
        env_id: str = "0",
        agent_token: str | None = None,
        dry_run: bool = True,
    ) -> Any:
        """Prune system resources for the given environment. Select what to prune via flags (containers, images, volumes, networks, build_cache). Volumes default to False. Use dry_run=True (default) to preview what would be pruned without making changes."""
        if dry_run:
            return {
                "dry_run": True,
                "warning": "Dry-run. Set dry_run=False to proceed.",
                "action": "prune_system",
                "target": f"system:{env_id}",
            }
        token = get_token_store().create(
            action="prune_system",
            target=f"system:{env_id}",
            endpoint=f"/api/environments/{env_id}/system/prune",
            method="POST",
            body={
                "containers": containers,
                "images": images,
                "volumes": volumes,
                "networks": networks,
                "buildCache": build_cache,
            },
            params=None,
            env_id=env_id,
            agent_token=agent_token,
        )
        return {
            "warning": "Destructive operation. Call confirm_operation(token=...) to proceed.",
            "confirmation_token": token,
            "target": f"system:{env_id}",
            "action": "prune_system",
        }

    @mcp.tool()
    async def get_system_health(env_id: str = "0", agent_token: str | None = None) -> Any:
        """Get system health metrics for the given environment."""
        client = require_client()
        url = "/api/health"
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
    async def check_system_upgrade(env_id: str = "0", agent_token: str | None = None) -> Any:
        """Check if a system upgrade is available for the given environment."""
        client = require_client()
        url = f"/api/environments/{env_id}/system/upgrade/check"
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
    async def trigger_upgrade(env_id: str = "0", agent_token: str | None = None) -> Any:
        """Trigger a system upgrade for the given environment."""
        token = get_token_store().create(
            action="trigger_upgrade",
            target=f"system:{env_id}",
            endpoint=f"/api/environments/{env_id}/system/upgrade",
            method="POST",
            body=None,
            params=None,
            env_id=env_id,
            agent_token=agent_token,
        )
        return {
            "warning": "Destructive operation. Call confirm_operation(token=...) to proceed.",
            "confirmation_token": token,
            "target": f"system:{env_id}",
            "action": "trigger_upgrade",
        }

    @mcp.tool()
    async def start_all_containers(
        env_id: str = "0",
        agent_token: str | None = None,
    ) -> Any:
        """Start all stopped containers for the given environment."""
        token = get_token_store().create(
            action="start_all_containers",
            target=f"system:{env_id}",
            endpoint=f"/api/environments/{env_id}/system/containers/start-all",
            method="POST",
            body=None,
            params=None,
            env_id=env_id,
            agent_token=agent_token,
        )
        return {
            "warning": "Destructive operation. Call confirm_operation(token=...) to proceed.",
            "confirmation_token": token,
            "target": f"system:{env_id}",
            "action": "start_all_containers",
        }

    @mcp.tool()
    async def start_stopped_containers(
        env_id: str = "0",
        agent_token: str | None = None,
    ) -> Any:
        """Start only containers that are currently stopped for the given environment."""
        token = get_token_store().create(
            action="start_stopped_containers",
            target=f"system:{env_id}",
            endpoint=f"/api/environments/{env_id}/system/containers/start-stopped",
            method="POST",
            body=None,
            params=None,
            env_id=env_id,
            agent_token=agent_token,
        )
        return {
            "warning": "Destructive operation. Call confirm_operation(token=...) to proceed.",
            "confirmation_token": token,
            "target": f"system:{env_id}",
            "action": "start_stopped_containers",
        }

    @mcp.tool()
    async def stop_all_containers(
        env_id: str = "0",
        agent_token: str | None = None,
    ) -> Any:
        """Stop all running containers for the given environment."""
        token = get_token_store().create(
            action="stop_all_containers",
            target=f"system:{env_id}",
            endpoint=f"/api/environments/{env_id}/system/containers/stop-all",
            method="POST",
            body=None,
            params=None,
            env_id=env_id,
            agent_token=agent_token,
        )
        return {
            "warning": "Destructive operation. Call confirm_operation(token=...) to proceed.",
            "confirmation_token": token,
            "target": f"system:{env_id}",
            "action": "stop_all_containers",
        }
