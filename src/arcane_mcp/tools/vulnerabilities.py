"""Vulnerability scanning tools.

v3 route notes: ignores are a collection at ``/vulnerabilities/ignored``
(``POST`` to create, ``DELETE /vulnerabilities/ignored/{ignoreId}`` to remove),
the scanner probe moved to ``/vulnerabilities/scanner``, and the aggregated
counts endpoint is ``/vulnerabilities/summary`` (``/overview`` is a different
shape: risk score, trend and drivers).
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
    async def get_vulnerability_summary_all(env_id: str = "0", agent_token: str | None = None) -> Any:
        """Get vulnerability summary across all scanned images."""
        client = require_client()
        url = await env_path(env_id, "/vulnerabilities/summary")
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
    async def list_all_vulnerabilities(env_id: str = "0", agent_token: str | None = None) -> Any:
        """List all vulnerabilities across the environment (paginated)."""
        url = await env_path(env_id, "/vulnerabilities/all")
        try:
            return await paginate_all(url, agent_token=agent_token)
        except httpx.HTTPStatusError as e:
            logger.warning("HTTP %s on %s: %s", e.response.status_code, url, e.response.text)
            return {"error": str(e), "status_code": e.response.status_code, "detail": e.response.text}
        except Exception as e:
            logger.exception("Unexpected error on %s", url)
            return {"error": str(e)}

    @mcp.tool()
    async def ignore_vulnerability(
        image_id: str,
        vulnerability_id: str,
        pkg_name: str,
        reason: str = "",
        env_id: str = "0",
        agent_token: str | None = None,
    ) -> Any:
        """Ignore a specific vulnerability.

        v3 keys an ignore record on the ``IgnoredVulnerability`` triple
        (``imageId``, ``vulnerabilityId``, ``pkgName``) — there is no single
        ``urn`` field any more. ``reason`` is free text stored with the record.
        """
        client = require_client()
        url = await env_path(env_id, "/vulnerabilities/ignored")
        payload: dict[str, Any] = {
            "imageId": image_id,
            "vulnerabilityId": vulnerability_id,
            "pkgName": pkg_name,
        }
        if reason:
            payload["reason"] = reason
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
    async def list_ignored_vulnerabilities(env_id: str = "0", agent_token: str | None = None) -> Any:
        """List all ignored vulnerabilities (paginated)."""
        url = await env_path(env_id, "/vulnerabilities/ignored")
        try:
            return await paginate_all(url, agent_token=agent_token)
        except httpx.HTTPStatusError as e:
            logger.warning("HTTP %s on %s: %s", e.response.status_code, url, e.response.text)
            return {"error": str(e), "status_code": e.response.status_code, "detail": e.response.text}
        except Exception as e:
            logger.exception("Unexpected error on %s", url)
            return {"error": str(e)}

    @mcp.tool()
    async def unignore_vulnerability(ignore_id: str, env_id: str = "0", agent_token: str | None = None) -> Any:
        """Un-ignore a previously ignored vulnerability. Requires confirmation via confirmation_token."""
        token = get_token_store().create(
            action="unignore_vulnerability",
            target=ignore_id,
            endpoint=await env_path(env_id, f"/vulnerabilities/ignored/{ignore_id}"),
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
            "operation_hash": compute_operation_hash("unignore_vulnerability", ignore_id, None, None),
            "target": ignore_id,
            "action": "unignore_vulnerability",
        }

    @mcp.tool()
    async def get_scanner_status(env_id: str = "0", agent_token: str | None = None) -> Any:
        """Get vulnerability scanner (Trivy) status."""
        client = require_client()
        url = await env_path(env_id, "/vulnerabilities/scanner")
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
