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

    @mcp.tool()
    async def get_image_counts(env_id: str = "0", agent_token: str | None = None) -> Any:
        """Get image count statistics for the environment."""
        client = require_client()
        url = f"/api/environments/{env_id}/images/counts"
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
    async def build_image(dockerfile_content: str, tag: str = "latest", env_id: str = "0", agent_token: str | None = None) -> Any:
        """Build an image from Dockerfile content."""
        client = require_client()
        url = f"/api/environments/{env_id}/images/build"
        body = {"dockerfile": dockerfile_content, "tag": tag}
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
    async def search_images(query: str, env_id: str = "0", agent_token: str | None = None) -> Any:
        """Search images by name/query in the environment."""
        client = require_client()
        url = f"/api/environments/{env_id}/images/search"
        params = {"query": query}
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
    async def upload_image(env_id: str = "0", agent_token: str | None = None) -> Any:
        """Upload an image to the environment.

        Note: This tool calls the upload endpoint but does NOT handle
        multipart file uploads. Use a direct API client (curl, Postman)
        with a multipart/form-data request for actual file uploads.
        """
        client = require_client()
        url = f"/api/environments/{env_id}/images/upload"
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
    async def get_image_history(image_id: str, env_id: str = "0", agent_token: str | None = None) -> Any:
        """Get the build history for an image."""
        client = require_client()
        url = f"/api/environments/{env_id}/images/{image_id}/history"
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
    async def get_image_export(name: str, env_id: str = "0", agent_token: str | None = None) -> Any:
        """Export an image by name (download its tar archive)."""
        client = require_client()
        url = f"/api/environments/{env_id}/images/{name}/export"
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
    async def get_image_attestations(name: str, env_id: str = "0", agent_token: str | None = None) -> Any:
        """Get attestations for an image."""
        client = require_client()
        url = f"/api/environments/{env_id}/images/{name}/attestations"
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
    async def scan_image_vulnerabilities(image_id: str, env_id: str = "0", agent_token: str | None = None) -> Any:
        """Trigger a vulnerability scan on an image."""
        client = require_client()
        url = f"/api/environments/{env_id}/images/{image_id}/vulnerabilities/scan"
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
    async def get_image_vulnerabilities(image_id: str, env_id: str = "0", agent_token: str | None = None) -> Any:
        """Get vulnerability report for an image."""
        client = require_client()
        url = f"/api/environments/{env_id}/images/{image_id}/vulnerabilities"
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
    async def get_vulnerability_summary(image_id: str, env_id: str = "0", agent_token: str | None = None) -> Any:
        """Get a summary of vulnerabilities for an image."""
        client = require_client()
        url = f"/api/environments/{env_id}/images/{image_id}/vulnerabilities/summary"
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
    async def check_image_update(reference: str, env_id: str = "0", agent_token: str | None = None) -> Any:
        """Check if a newer version of an image is available by reference."""
        client = require_client()
        url = f"/api/environments/{env_id}/image-updates/check"
        params = {"reference": reference}
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
    async def check_all_image_updates(env_id: str = "0", agent_token: str | None = None) -> Any:
        """Check for updates on all images in the environment."""
        client = require_client()
        url = f"/api/environments/{env_id}/image-updates/check-all"
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
    async def get_image_update_summary(env_id: str = "0", agent_token: str | None = None) -> Any:
        """Get a summary of available image updates."""
        client = require_client()
        url = f"/api/environments/{env_id}/image-updates/summary"
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
