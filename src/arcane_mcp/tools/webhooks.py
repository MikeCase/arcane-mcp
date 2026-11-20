"""Webhook CRUD tools.

v3 removed the inbound ``/api/webhooks/trigger/{token}`` endpoint entirely (only
``/agents/{id}/webhooks`` CRUD remains in the spec), so :func:`trigger_webhook`
returns an explanatory notice and issues no request. ``PATCH /webhooks/{id}`` is
the update verb; the created token is returned once, at creation time.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx
from fastmcp import FastMCP

from ..client import _build_headers, env_path, paginate_all, require_client
from ..safety import ToolClass, compute_operation_hash, get_token_store

logger = logging.getLogger(__name__)


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    async def trigger_webhook(token: str, action: str) -> Any:
        """Trigger an Arcane inbound webhook by token (removed in Arcane v3)."""
        return {
            "error": "Webhook trigger endpoints were removed in Arcane v3; use /webhooks CRUD instead.",
            "removed_in": "Arcane v3.0.0",
            "requested": {"token": token, "action": action},
            "alternatives": [
                "create_webhook(name=..., target_type=..., action_type=..., target_id=...) "
                "returns the token once; the trigger URL is served by the Arcane UI, not this API",
                "update_webhook(webhook_id, enabled=...) to pause or resume a hook",
            ],
        }

    @mcp.tool()
    async def list_webhooks(env_id: str = "0", agent_token: str | None = None) -> Any:
        """List all webhooks for the given environment."""
        url = await env_path(env_id, "/webhooks")
        try:
            return await paginate_all(url, agent_token=agent_token)
        except httpx.HTTPStatusError as e:
            logger.warning("HTTP %s on %s: %s", e.response.status_code, url, e.response.text)
            return {"error": str(e), "status_code": e.response.status_code, "detail": e.response.text}
        except Exception as e:
            logger.exception("Unexpected error on %s", url)
            return {"error": str(e)}

    @mcp.tool()
    async def create_webhook(
        name: str,
        target_type: str,
        action_type: str,
        target_id: str = "",
        env_id: str = "0",
        agent_token: str | None = None,
    ) -> Any:
        """Create a webhook that triggers a container, project or updater action.

        ``target_type`` is ``container``, ``project``, ``updater`` or ``gitops``;
        ``action_type`` is one of ``update``, ``start``, ``stop``, ``restart``,
        ``redeploy``, ``up``, ``down``, ``run``, ``sync``. ``target_id`` may be
        empty for ``updater`` webhooks. The response carries the webhook token —
        it is shown once and never returned again.
        """
        client = require_client()
        api_url = await env_path(env_id, "/webhooks")
        body: dict[str, Any] = {
            "name": name,
            "targetType": target_type,
            "actionType": action_type,
        }
        if target_id:
            body["targetId"] = target_id
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
        webhook_id: str,
        enabled: bool,
        env_id: str = "0",
        agent_token: str | None = None,
    ) -> Any:
        """Enable or disable a webhook."""
        client = require_client()
        api_url = await env_path(env_id, f"/webhooks/{webhook_id}")
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
        webhook_id: str,
        env_id: str = "0",
        agent_token: str | None = None,
    ) -> Any:
        """Delete a webhook. Destructive; requires confirmation via confirmation_token."""
        token = get_token_store().create(
            action="delete_webhook",
            target=webhook_id,
            endpoint=await env_path(env_id, f"/webhooks/{webhook_id}"),
            method="DELETE",
            body=None,
            params=None,
            classification=ToolClass.DESTRUCTIVE_WRITE,
            env_id=env_id,
            agent_token=agent_token,
        )
        return {
            "warning": "Destructive operation. Call confirm_operation(token=...) to proceed.",
            "confirmation_token": token,
            "classification": ToolClass.DESTRUCTIVE_WRITE,
            "operation_hash": compute_operation_hash("delete_webhook", webhook_id, None, None),
            "target": webhook_id,
            "action": "delete_webhook",
        }
