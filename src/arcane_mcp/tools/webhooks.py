"""Webhook trigger and CRUD tools."""
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
    async def trigger_webhook(token: str, action: str) -> Any:
        """Trigger an Arcane inbound webhook by token."""
        client = require_client()
        url = f"/api/webhooks/trigger/{token}"
        body = {"action": action}
        try:
            resp = await client.post(url, json=body)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            logger.warning("HTTP %s on %s: %s", resp.status_code, url, resp.text)
            return {"error": str(e), "status_code": resp.status_code, "detail": resp.text}
        except Exception as e:
            logger.exception("Unexpected error on %s", url)
            return {"error": str(e)}

    @mcp.tool()
    async def list_webhooks(env_id: str = "0", agent_token: str | None = None) -> Any:
        """List all webhooks for the given environment."""
        client = require_client()
        url = f"/api/environments/{env_id}/webhooks"
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
    async def create_webhook(
        name: str, url: str, env_id: str = "0", agent_token: str | None = None,
    ) -> Any:
        """Create a new webhook in the given environment."""
        client = require_client()
        api_url = f"/api/environments/{env_id}/webhooks"
        body: dict[str, Any] = {"name": name, "url": url}
        try:
            resp = await client.post(api_url, json=body, headers=_build_headers(agent_token))
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            logger.warning("HTTP %s on %s: %s", resp.status_code, api_url, resp.text)
            return {"error": str(e), "status_code": resp.status_code, "detail": resp.text}
        except Exception as e:
            logger.exception("Unexpected error on %s", api_url)
            return {"error": str(e)}

    @mcp.tool()
    async def update_webhook(
        webhook_id: str, enabled: bool, env_id: str = "0", agent_token: str | None = None,
    ) -> Any:
        """Enable or disable a webhook."""
        client = require_client()
        api_url = f"/api/environments/{env_id}/webhooks/{webhook_id}"
        body = {"enabled": enabled}
        try:
            resp = await client.patch(api_url, json=body, headers=_build_headers(agent_token))
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            logger.warning("HTTP %s on %s: %s", resp.status_code, api_url, resp.text)
            return {"error": str(e), "status_code": resp.status_code, "detail": resp.text}
        except Exception as e:
            logger.exception("Unexpected error on %s", api_url)
            return {"error": str(e)}

    @mcp.tool()
    async def delete_webhook(
        webhook_id: str, env_id: str = "0",
        agent_token: str | None = None,
    ) -> Any:
        """Delete a webhook. Destructive; requires confirmation via confirmation_token."""
        token = get_token_store().create(
            action="delete_webhook",
            target=webhook_id,
            endpoint=f"/api/environments/{env_id}/webhooks/{webhook_id}",
            method="DELETE",
            body=None,
            params=None,
            classification=ToolClass.DESTRUCTIVE_WRITE,
            env_id=env_id,
            agent_token=agent_token,
        )
        return {"warning": "Destructive operation. Call confirm_operation(token=...) to proceed.", "confirmation_token": token, "classification": ToolClass.DESTRUCTIVE_WRITE, "operation_hash": compute_operation_hash("delete_webhook", webhook_id, None, None), "target": webhook_id, "action": "delete_webhook"}
