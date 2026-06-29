"""Network management tools."""
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
    async def remove_network(network_id: str, env_id: str = "0", agent_token: str | None = None) -> Any:
        """Remove a network. Destructive; requires confirmation token."""
        token = get_token_store().create(
            action="remove_network",
            target=f"network:{network_id}",
            endpoint=f"/api/environments/{env_id}/networks/{network_id}",
            method="DELETE",
            env_id=env_id,
            agent_token=agent_token,
        )
        return {
            "warning": "Destructive operation. Call confirm_operation(token=...) to proceed.",
            "confirmation_token": token,
            "target": f"network:{network_id}",
            "action": "remove_network",
        }

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
    async def prune_networks(env_id: str = "0", agent_token: str | None = None, dry_run: bool = True) -> Any:
        """Prune unused Docker networks. Destructive; use dry_run=False and confirm to execute."""
        if dry_run:
            return {
                "dry_run": True,
                "warning": "Dry-run. Set dry_run=False and confirm to execute.",
                "action": "prune_networks",
                "target": "all",
            }
        token = get_token_store().create(
            action="prune_networks",
            target="all",
            endpoint=f"/api/environments/{env_id}/networks/prune",
            method="POST",
            env_id=env_id,
            agent_token=agent_token,
        )
        return {
            "warning": "Destructive operation. Call confirm_operation(token=...) to proceed.",
            "confirmation_token": token,
            "target": "all",
            "action": "prune_networks",
        }

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
