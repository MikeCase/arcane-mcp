"""Network management tools."""
from __future__ import annotations

import logging
from typing import Any

import httpx
from fastmcp import FastMCP

from ..client import _build_headers, require_client

logger = logging.getLogger(__name__)


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    async def list_networks(env_id: str = "0", agent_token: str | None = None) -> Any:
        """List all networks in the given environment."""
        client = require_client()
        url = f"/api/environments/{env_id}/networks"
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
    async def create_network(name: str, driver: str = "bridge", env_id: str = "0", agent_token: str | None = None) -> Any:
        """Create a new network in the given environment."""
        client = require_client()
        url = f"/api/environments/{env_id}/networks"
        payload = {"name": name, "driver": driver}
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
    async def inspect_network(network_id: str, env_id: str = "0", agent_token: str | None = None) -> Any:
        """Inspect a specific network."""
        client = require_client()
        url = f"/api/environments/{env_id}/networks/{network_id}"
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
    async def remove_network(network_id: str, env_id: str = "0", agent_token: str | None = None, confirm: bool = False) -> Any:
        """Remove a network. Requires confirm=True to execute."""
        if not confirm:
            return {"warning": "Destructive operation. Set confirm=True to remove this network.", "network_id": network_id}
        client = require_client()
        url = f"/api/environments/{env_id}/networks/{network_id}"
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
    async def connect_container_to_network(network_id: str, container_id: str, env_id: str = "0", agent_token: str | None = None) -> Any:
        """Connect a container to a network."""
        client = require_client()
        url = f"/api/environments/{env_id}/networks/{network_id}/connect"
        payload = {"container": container_id}
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
    async def disconnect_container_from_network(
        network_id: str, container_id: str, env_id: str = "0",
        agent_token: str | None = None,
    ) -> Any:
        """Disconnect a container from a network."""
        client = require_client()
        url = f"/api/environments/{env_id}/networks/{network_id}/disconnect"
        payload = {"container": container_id}
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
    async def prune_networks(env_id: str = "0", agent_token: str | None = None, confirm: bool = False) -> Any:
        """Prune unused Docker networks. Destructive; requires confirm=True."""
        if not confirm:
            return {"warning": "Destructive operation. Set confirm=True to prune unused networks."}
        client = require_client()
        url = f"/api/environments/{env_id}/networks/prune"
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
    async def get_network_counts(env_id: str = "0", agent_token: str | None = None) -> Any:
        """Get network counts for the given environment."""
        client = require_client()
        url = f"/api/environments/{env_id}/networks/counts"
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
    async def get_network_topology(env_id: str = "0", agent_token: str | None = None) -> Any:
        """Get network topology for the given environment."""
        client = require_client()
        url = f"/api/environments/{env_id}/networks/topology"
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
