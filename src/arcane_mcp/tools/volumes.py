"""Volume management tools."""
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
    async def list_volumes(env_id: str = "0", agent_token: str | None = None) -> Any:
        """List all volumes in the given environment."""
        client = require_client()
        url = f"/api/environments/{env_id}/volumes"
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
    async def create_volume(
        name: str, driver: str = "local", labels: str | None = None,
        env_id: str = "0", agent_token: str | None = None,
    ) -> Any:
        """Create a new volume in the given environment."""
        client = require_client()
        url = f"/api/environments/{env_id}/volumes"
        body: dict[str, Any] = {"name": name, "driver": driver}
        if labels:
            body["labels"] = labels
        try:
            resp = await client.post(url, json=body, headers=_build_headers(agent_token))
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            logger.warning("HTTP %s on %s: %s", resp.status_code, url, resp.text)
            return {"error": str(e), "status_code": resp.status_code, "detail": resp.text}
        except Exception as e:
            logger.exception("Unexpected error on %s", url)
            return {"error": str(e)}

    @mcp.tool()
    async def inspect_volume(name: str, env_id: str = "0", agent_token: str | None = None) -> Any:
        """Inspect a volume by name."""
        client = require_client()
        url = f"/api/environments/{env_id}/volumes/{name}"
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
    async def remove_volume(
        name: str, force: bool = False, env_id: str = "0",
        agent_token: str | None = None,
    ) -> Any:
        """Remove a volume by name. Destructive; requires confirmation token."""
        token = get_token_store().create(
            action="remove_volume",
            target=f"volume:{name}",
            endpoint=f"/api/environments/{env_id}/volumes/{name}",
            method="DELETE",
            body={"force": str(force).lower()},
            env_id=env_id,
            agent_token=agent_token,
        )
        return {
            "warning": "Destructive operation. Call confirm_operation(token=...) to proceed.",
            "confirmation_token": token,
            "target": f"volume:{name}",
            "action": "remove_volume",
        }

    @mcp.tool()
    async def prune_volumes(env_id: str = "0", agent_token: str | None = None, dry_run: bool = True) -> Any:
        """Prune unused Docker volumes. Destructive; use dry_run=False and confirm to execute."""
        if dry_run:
            return {
                "dry_run": True,
                "warning": "Dry-run. Set dry_run=False and confirm to execute.",
                "action": "prune_volumes",
                "target": "all",
            }
        token = get_token_store().create(
            action="prune_volumes",
            target="all",
            endpoint=f"/api/environments/{env_id}/volumes/prune",
            method="POST",
            env_id=env_id,
            agent_token=agent_token,
        )
        return {
            "warning": "Destructive operation. Call confirm_operation(token=...) to proceed.",
            "confirmation_token": token,
            "target": "all",
            "action": "prune_volumes",
        }

    # ── Volume counts & sizes ──────────────────────────────────────────────

    @mcp.tool()
    async def get_volume_counts(env_id: str = "0", agent_token: str | None = None) -> Any:
        """Get volume counts for the given environment."""
        client = require_client()
        url = f"/api/environments/{env_id}/volumes/counts"
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
    async def get_volume_sizes(env_id: str = "0", agent_token: str | None = None) -> Any:
        """Get volume sizes for the given environment."""
        client = require_client()
        url = f"/api/environments/{env_id}/volumes/sizes"
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
    async def get_volume_usage(name: str, env_id: str = "0", agent_token: str | None = None) -> Any:
        """Get disk usage for a specific volume."""
        client = require_client()
        url = f"/api/environments/{env_id}/volumes/{name}/usage"
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

    # ── Volume backups ─────────────────────────────────────────────────────

    @mcp.tool()
    async def list_volume_backups(name: str, env_id: str = "0", agent_token: str | None = None) -> Any:
        """List all backups for a volume."""
        client = require_client()
        url = f"/api/environments/{env_id}/volumes/{name}/backups"
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
    async def create_volume_backup(name: str, env_id: str = "0", agent_token: str | None = None) -> Any:
        """Create a new backup of a volume."""
        client = require_client()
        url = f"/api/environments/{env_id}/volumes/{name}/backups"
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
    async def restore_volume_backup(
        volume_name: str, backup_id: str, env_id: str = "0",
        agent_token: str | None = None,
    ) -> Any:
        """Restore a volume backup. Destructive; requires confirmation token."""
        token = get_token_store().create(
            action="restore_volume_backup",
            target=f"volume:{volume_name}/backup:{backup_id}",
            endpoint=f"/api/environments/{env_id}/volumes/{volume_name}/backups/{backup_id}/restore",
            method="POST",
            env_id=env_id,
            agent_token=agent_token,
        )
        return {
            "warning": "Destructive operation. Call confirm_operation(token=...) to proceed.",
            "confirmation_token": token,
            "target": f"volume:{volume_name}/backup:{backup_id}",
            "action": "restore_volume_backup",
        }

    @mcp.tool()
    async def delete_volume_backup(
        backup_id: str, env_id: str = "0",
        agent_token: str | None = None,
    ) -> Any:
        """Delete a volume backup. Destructive; requires confirmation token."""
        token = get_token_store().create(
            action="delete_volume_backup",
            target=f"backup:{backup_id}",
            endpoint=f"/api/environments/{env_id}/volumes/backups/{backup_id}",
            method="DELETE",
            env_id=env_id,
            agent_token=agent_token,
        )
        return {
            "warning": "Destructive operation. Call confirm_operation(token=...) to proceed.",
            "confirmation_token": token,
            "target": f"backup:{backup_id}",
            "action": "delete_volume_backup",
        }

    @mcp.tool()
    async def download_volume_backup(backup_id: str, env_id: str = "0", agent_token: str | None = None) -> Any:
        """Download a volume backup."""
        client = require_client()
        url = f"/api/environments/{env_id}/volumes/backups/{backup_id}/download"
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

    # ── Volume file browser ────────────────────────────────────────────────

    @mcp.tool()
    async def browse_volume(
        name: str, path: str = "/", env_id: str = "0",
        agent_token: str | None = None,
    ) -> Any:
        """List files and directories at a path inside a volume."""
        client = require_client()
        url = f"/api/environments/{env_id}/volumes/{name}/browse"
        params = {"path": path}
        try:
            resp = await client.get(url, params=params, headers=_build_headers(agent_token))
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            logger.warning("HTTP %s on %s: %s", resp.status_code, url, resp.text)
            return {"error": str(e), "status_code": resp.status_code, "detail": resp.text}
        except Exception as e:
            logger.exception("Unexpected error on %s", url)
            return {"error": str(e)}

    @mcp.tool()
    async def read_volume_file(
        name: str, path: str, env_id: str = "0",
        agent_token: str | None = None,
    ) -> Any:
        """Read the contents of a file inside a volume."""
        client = require_client()
        url = f"/api/environments/{env_id}/volumes/{name}/browse/content"
        params = {"path": path}
        try:
            resp = await client.get(url, params=params, headers=_build_headers(agent_token))
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            logger.warning("HTTP %s on %s: %s", resp.status_code, url, resp.text)
            return {"error": str(e), "status_code": resp.status_code, "detail": resp.text}
        except Exception as e:
            logger.exception("Unexpected error on %s", url)
            return {"error": str(e)}

    @mcp.tool()
    async def create_volume_directory(
        name: str, path: str, env_id: str = "0",
        agent_token: str | None = None,
    ) -> Any:
        """Create a directory inside a volume."""
        client = require_client()
        url = f"/api/environments/{env_id}/volumes/{name}/browse/mkdir"
        body = {"path": path}
        try:
            resp = await client.post(url, json=body, headers=_build_headers(agent_token))
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            logger.warning("HTTP %s on %s: %s", resp.status_code, url, resp.text)
            return {"error": str(e), "status_code": resp.status_code, "detail": resp.text}
        except Exception as e:
            logger.exception("Unexpected error on %s", url)
            return {"error": str(e)}

    @mcp.tool()
    async def upload_to_volume(
        name: str, path: str, content: str, env_id: str = "0",
        agent_token: str | None = None,
    ) -> Any:
        """Upload a file to a path inside a volume."""
        client = require_client()
        url = f"/api/environments/{env_id}/volumes/{name}/browse/upload"
        body = {"path": path, "content": content}
        try:
            resp = await client.post(url, json=body, headers=_build_headers(agent_token))
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            logger.warning("HTTP %s on %s: %s", resp.status_code, url, resp.text)
            return {"error": str(e), "status_code": resp.status_code, "detail": resp.text}
        except Exception as e:
            logger.exception("Unexpected error on %s", url)
            return {"error": str(e)}

    @mcp.tool()
    async def delete_volume_file(
        name: str, path: str, env_id: str = "0",
        agent_token: str | None = None,
    ) -> Any:
        """Delete a file or directory inside a volume. Destructive; requires confirmation token."""
        token = get_token_store().create(
            action="delete_volume_file",
            target=f"volume:{name}:{path}",
            endpoint=f"/api/environments/{env_id}/volumes/{name}/browse",
            method="DELETE",
            params={"path": path},
            env_id=env_id,
            agent_token=agent_token,
        )
        return {
            "warning": "Destructive operation. Call confirm_operation(token=...) to proceed.",
            "confirmation_token": token,
            "target": f"volume:{name}:{path}",
            "action": "delete_volume_file",
        }
