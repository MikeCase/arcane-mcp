"""System-level tools."""
from __future__ import annotations

import logging
from typing import Any

import httpx
from fastmcp import FastMCP

from ..client import _build_headers, require_client

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
        confirm: bool = False,
    ) -> Any:
        """Prune system resources for the given environment. Select what to prune via flags (containers, images, volumes, networks, build_cache). Volumes default to False."""
        if not confirm:
            return {
                "warning": "Destructive operation. Set confirm=True to prune system resources.",
                "containers": containers,
                "images": images,
                "volumes": volumes,
                "networks": networks,
                "build_cache": build_cache,
            }
        client = require_client()
        url = f"/api/environments/{env_id}/system/prune"
        payload = {
            "containers": containers,
            "images": images,
            "volumes": volumes,
            "networks": networks,
            "buildCache": build_cache,
        }
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
