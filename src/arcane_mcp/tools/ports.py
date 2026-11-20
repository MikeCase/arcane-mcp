"""Port mapping tools."""

from __future__ import annotations

import logging
from typing import Any

import httpx
from fastmcp import FastMCP

from ..client import env_path, paginate_all

logger = logging.getLogger(__name__)


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    async def list_ports(env_id: str = "0", agent_token: str | None = None) -> Any:
        """List all port mappings for the given environment (paginated)."""
        url = await env_path(env_id, "/ports")
        try:
            return await paginate_all(url, agent_token=agent_token)
        except httpx.HTTPStatusError as e:
            logger.warning("HTTP %s on %s: %s", e.response.status_code, url, e.response.text)
            return {"error": str(e), "status_code": e.response.status_code, "detail": e.response.text}
        except Exception as e:
            logger.exception("Unexpected error on %s", url)
            return {"error": str(e)}
