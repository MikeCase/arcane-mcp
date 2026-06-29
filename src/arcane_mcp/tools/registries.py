"""Container registry management tools."""
from __future__ import annotations

import logging
from typing import Any

import httpx
from fastmcp import FastMCP

from ..client import _build_headers, require_client

logger = logging.getLogger(__name__)


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    async def list_registries(env_id: str = "0", agent_token: str | None = None) -> Any:
        """List all container registries."""
        client = require_client()
        url = "/api/container-registries"
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
    async def create_registry(name: str, url: str, username: str = "", password: str = "", env_id: str = "0", agent_token: str | None = None) -> Any:
        """Create a new container registry."""
        client = require_client()
        url_path = "/api/container-registries"
        payload = {"name": name, "url": url, "username": username, "password": password}
        try:
            resp = await client.post(url_path, json=payload, headers=_build_headers(agent_token))
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            logger.warning("HTTP %s on %s: %s", resp.status_code, url_path, resp.text)
            return {"error": str(e), "status_code": resp.status_code, "detail": resp.text}
        except Exception as e:
            logger.exception("Unexpected error on %s", url_path)
            return {"error": str(e)}

    @mcp.tool()
    async def get_registry(registry_id: str, env_id: str = "0", agent_token: str | None = None) -> Any:
        """Get a container registry by ID."""
        client = require_client()
        url = f"/api/container-registries/{registry_id}"
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
    async def update_registry(registry_id: str, name: str | None = None, url: str | None = None, username: str | None = None, password: str | None = None, env_id: str = "0", agent_token: str | None = None) -> Any:
        """Update a container registry."""
        client = require_client()
        url_path = f"/api/container-registries/{registry_id}"
        payload: dict[str, Any] = {}
        if name is not None:
            payload["name"] = name
        if url is not None:
            payload["url"] = url
        if username is not None:
            payload["username"] = username
        if password is not None:
            payload["password"] = password
        if not payload:
            return {"warning": "No update payload provided."}
        try:
            resp = await client.put(url_path, json=payload, headers=_build_headers(agent_token))
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            logger.warning("HTTP %s on %s: %s", resp.status_code, url_path, resp.text)
            return {"error": str(e), "status_code": resp.status_code, "detail": resp.text}
        except Exception as e:
            logger.exception("Unexpected error on %s", url_path)
            return {"error": str(e)}

    @mcp.tool()
    async def delete_registry(registry_id: str, env_id: str = "0", agent_token: str | None = None, confirm: bool = False) -> Any:
        """Delete a container registry. Requires confirm=True."""
        if not confirm:
            return {"warning": "Destructive operation. Set confirm=True to delete this registry.", "registry_id": registry_id}
        client = require_client()
        url = f"/api/container-registries/{registry_id}"
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
    async def test_registry(registry_id: str, env_id: str = "0", agent_token: str | None = None) -> Any:
        """Test connectivity to a container registry."""
        client = require_client()
        url = f"/api/container-registries/{registry_id}/test"
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
