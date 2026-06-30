"""Vulnerability scanning tools."""
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
    async def get_vulnerability_summary_all(env_id: str = "0", agent_token: str | None = None) -> Any:
        """Get vulnerability summary across all scanned images."""
        client = require_client()
        url = f"/api/environments/{env_id}/vulnerabilities/summary"
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
        """List all vulnerabilities across the environment."""
        client = require_client()
        url = f"/api/environments/{env_id}/vulnerabilities/all"
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
    async def ignore_vulnerability(urn: str, env_id: str = "0", agent_token: str | None = None) -> Any:
        """Ignore a specific vulnerability by URN."""
        client = require_client()
        url = f"/api/environments/{env_id}/vulnerabilities/ignore"
        payload = {"urn": urn}
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
        """List all ignored vulnerabilities."""
        client = require_client()
        url = f"/api/environments/{env_id}/vulnerabilities/ignored"
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
    async def unignore_vulnerability(ignore_id: str, env_id: str = "0", agent_token: str | None = None) -> Any:
        """Un-ignore a previously ignored vulnerability. Requires confirmation via confirmation_token."""
        token = get_token_store().create(
            action="unignore_vulnerability",
            target=ignore_id,
            endpoint=f"/api/environments/{env_id}/vulnerabilities/ignore/{ignore_id}",
            method="DELETE",
            body=None,
            params=None,
            classification=ToolClass.DESTRUCTIVE_WRITE,
            env_id=env_id,
            agent_token=agent_token,
        )
        return {"warning": "Destructive operation. Call confirm_operation(token=...) to proceed.", "confirmation_token": token, "classification": ToolClass.DESTRUCTIVE_WRITE, "operation_hash": compute_operation_hash("unignore_vulnerability", ignore_id, None, None), "target": ignore_id, "action": "unignore_vulnerability"}

    @mcp.tool()
    async def get_scanner_status(env_id: str = "0", agent_token: str | None = None) -> Any:
        """Get vulnerability scanner (Trivy) status."""
        client = require_client()
        url = f"/api/environments/{env_id}/vulnerabilities/scanner-status"
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
