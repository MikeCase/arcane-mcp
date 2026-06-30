"""Activity and event tools."""
from __future__ import annotations

import logging
from typing import Any

import httpx
from fastmcp import FastMCP

from ..client import _build_headers, require_client
from ..safety import ToolClass, compute_operation_hash, get_token_store

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
    async def clear_activity_history(env_id: str = "0", agent_token: str | None = None, dry_run: bool = True) -> Any:
        """Clear activity history for an environment. Requires confirmation via confirmation_token."""
        if dry_run:
            return {"warning": "Dry-run: would clear activity history. Set dry_run=False and call confirm_operation(token=...) to proceed.", "target": env_id, "action": "clear_activity_history"}
        token = get_token_store().create(
            action="clear_activity_history",
            target=env_id,
            endpoint=f"/api/environments/{env_id}/activities/history",
            method="DELETE",
            body=None,
            params=None,
            classification=ToolClass.DESTRUCTIVE_WRITE,
            env_id=env_id,
            agent_token=agent_token,
        )
        return {"warning": "Destructive operation. Call confirm_operation(token=...) to proceed.", "confirmation_token": token, "classification": ToolClass.DESTRUCTIVE_WRITE, "operation_hash": compute_operation_hash("clear_activity_history", env_id, None, None), "target": env_id, "action": "clear_activity_history"}

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
    async def delete_event(event_id: str, agent_token: str | None = None) -> Any:
        """Delete a system event. Requires confirmation via confirmation_token."""
        token = get_token_store().create(
            action="delete_event",
            target=event_id,
            endpoint=f"/api/events/{event_id}",
            method="DELETE",
            body=None,
            params=None,
            classification=ToolClass.DESTRUCTIVE_WRITE,
            env_id=None,
            agent_token=agent_token,
        )
        return {"warning": "Destructive operation. Call confirm_operation(token=...) to proceed.", "confirmation_token": token, "classification": ToolClass.DESTRUCTIVE_WRITE, "operation_hash": compute_operation_hash("delete_event", event_id, None, None), "target": event_id, "action": "delete_event"}
