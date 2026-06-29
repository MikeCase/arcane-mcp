"""Activity and event tools."""
from __future__ import annotations

import logging
from typing import Any

import httpx
from fastmcp import FastMCP

from ..client import _build_headers, require_client

logger = logging.getLogger(__name__)


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    async def list_activities(env_id: str = "0", agent_token: str | None = None) -> Any:
        """List current and recent background activities for an environment."""
        client = require_client()
        url = f"/api/environments/{env_id}/activities"
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
    async def get_activity(activity_id: str, env_id: str = "0", agent_token: str | None = None) -> Any:
        """Get a specific background activity."""
        client = require_client()
        url = f"/api/environments/{env_id}/activities/{activity_id}"
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
    async def cancel_activity(activity_id: str, env_id: str = "0", agent_token: str | None = None) -> Any:
        """Cancel a running background activity."""
        client = require_client()
        url = f"/api/environments/{env_id}/activities/{activity_id}/cancel"
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
    async def clear_activity_history(env_id: str = "0", agent_token: str | None = None, confirm: bool = False) -> Any:
        """Clear activity history for an environment. Requires confirm=True."""
        if not confirm:
            return {"warning": "Destructive operation. Set confirm=True to clear activity history."}
        client = require_client()
        url = f"/api/environments/{env_id}/activities/history"
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
    async def list_events(agent_token: str | None = None) -> Any:
        """List system events (paginated, across all environments)."""
        client = require_client()
        url = "/api/events"
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
    async def get_environment_events(environment_id: str, agent_token: str | None = None) -> Any:
        """Get events for a specific environment."""
        client = require_client()
        url = f"/api/events/environment/{environment_id}"
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
    async def delete_event(event_id: str, agent_token: str | None = None, confirm: bool = False) -> Any:
        """Delete a system event. Requires confirm=True."""
        if not confirm:
            return {"warning": "Destructive operation. Set confirm=True to delete this event.", "event_id": event_id}
        client = require_client()
        url = f"/api/events/{event_id}"
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
