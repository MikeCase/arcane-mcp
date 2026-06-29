"""Image management tools."""
from __future__ import annotations

import logging
from typing import Any

import httpx
from fastmcp import FastMCP

from ..client import _build_headers, require_client

logger = logging.getLogger(__name__)


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    async def list_images(env_id: str = "0", agent_token: str | None = None) -> Any:
        """List all images in the given environment."""
        client = require_client()
        url = f"/api/environments/{env_id}/images"
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
    async def pull_image(repository: str, tag: str = "latest", env_id: str = "0", agent_token: str | None = None) -> Any:
        """Pull image from registry into environment."""
        client = require_client()
        url = f"/api/environments/{env_id}/images/pull"
        body = {"repository": repository, "tag": tag}
        try:
            resp = await client.post(url, json=body, headers=_build_headers(agent_token))
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            logger.warning("HTTP %s on %s: %s", resp.status_code, url, resp.text)
            return {"error": str(e), "status_code": resp.status_code, "detail": resp.text}
        except Exception as e:
            logger.exception("Unexpected error on %s", url)
            return {"error": str(e)}

    @mcp.tool()
    async def remove_image(
        image_id: str, force: bool = False, env_id: str = "0",
        agent_token: str | None = None, confirm: bool = False,
    ) -> Any:
        """Remove image by id. Destructive; requires confirm=True."""
        if not confirm:
            return {"warning": "Destructive operation requires confirm=True to proceed."}
        client = require_client()
        url = f"/api/environments/{env_id}/images/{image_id}"
        body = {"force": str(force).lower()}
        try:
            resp = await client.request("DELETE", url, json=body, headers=_build_headers(agent_token))
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            logger.warning("HTTP %s on %s: %s", resp.status_code, url, resp.text)
            return {"error": str(e), "status_code": resp.status_code, "detail": resp.text}
        except Exception as e:
            logger.exception("Unexpected error on %s", url)
            return {"error": str(e)}

    @mcp.tool()
    async def inspect_image(image_id: str, env_id: str = "0", agent_token: str | None = None) -> Any:
        """Inspect image by id."""
        client = require_client()
        url = f"/api/environments/{env_id}/images/{image_id}"
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
    async def tag_image(source: str, target: str, env_id: str = "0", agent_token: str | None = None) -> Any:
        """Tag an existing image with a new repository name."""
        client = require_client()
        url = f"/api/environments/{env_id}/images/{source}/tag"
        body = {"repo": target}
        try:
            resp = await client.post(url, json=body, headers=_build_headers(agent_token))
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            logger.warning("HTTP %s on %s: %s", resp.status_code, url, resp.text)
            return {"error": str(e), "status_code": resp.status_code, "detail": resp.text}
        except Exception as e:
            logger.exception("Unexpected error on %s", url)
            return {"error": str(e)}

    @mcp.tool()
    async def prune_images(env_id: str = "0", agent_token: str | None = None, confirm: bool = False) -> Any:
        """Prune unused Docker images. Destructive; requires confirm=True."""
        if not confirm:
            return {"warning": "Destructive operation. Set confirm=True to prune unused images."}
        client = require_client()
        url = f"/api/environments/{env_id}/images/prune"
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
