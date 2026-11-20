"""Volume management tools (Arcane v3).

Every route here was checked against the v3.1 ``/api/openapi.json`` spec:

* the collection and per-volume reads are unchanged;
* lists paginate at 20 items, so ``list_volumes`` / ``list_volume_backups`` go
  through :func:`paginate_all` and return one merged envelope;
* restore moved from ``POST /volumes/{name}/backups/{id}/restore`` onto a query
  action: ``POST /volumes/{name}/backups/{id}?action=restore``;
* ``DELETE /volumes/{name}`` takes ``force`` as a *query* parameter, not a body;
* the v2 file browser (``/volumes/{name}/browse*``) is gone. Reads live on the
  workspace API (``GET /volumes/{name}/workspace`` and
  ``.../workspace/file``); writes need a workspace manifest
  (``PATCH /volumes/{name}/workspace``) that this server does not implement yet,
  so ``create_volume_directory`` / ``upload_to_volume`` / ``delete_volume_file``
  answer with an explicit "not supported" notice and send no request.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx
from fastmcp import FastMCP

from ..client import _build_headers, env_path, paginate_all, parse_stream_response, require_client
from ..safety import ToolClass, compute_operation_hash, get_token_store

logger = logging.getLogger(__name__)

_WORKSPACE_WRITE_REASON = (
    "Arcane v3 removed the volume file-browser write routes. Creating, uploading and "
    "deleting files inside a volume now requires a workspace manifest: a "
    "PATCH /volumes/{volumeName}/workspace request with a JSON `manifest` part (and, for "
    "uploads, multipart `files` parts referenced by the manifest). This server does not "
    "implement that manifest yet."
)


def _labels_to_dict(labels: str | None) -> dict[str, str] | None:
    """Parse ``"a=1,b=2"`` into the ``{key: value}`` map v3's Volume schema expects."""
    if not labels:
        return None
    parsed: dict[str, str] = {}
    for pair in labels.split(","):
        pair = pair.strip()
        if not pair:
            continue
        key, _, value = pair.partition("=")
        parsed[key.strip()] = value.strip()
    return parsed or None


def _unsupported_workspace_write(action: str, target: str, alternative: str) -> dict[str, Any]:
    """Uniform 'not supported on v3' answer. Sends no HTTP request and mints no token."""
    return {
        "error": "not_supported",
        "supported": False,
        "action": action,
        "target": target,
        "reason": _WORKSPACE_WRITE_REASON,
        "alternative": alternative,
        "warning": "No request was sent. Do not retry this tool expecting a different result.",
    }


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    async def list_volumes(env_id: str = "0", agent_token: str | None = None) -> Any:
        """List all volumes in the given environment (every page, not just the first 20)."""
        url = await env_path(env_id, "/volumes")
        try:
            return await paginate_all(url, agent_token=agent_token)
        except httpx.HTTPStatusError as e:
            logger.warning("HTTP %s on %s: %s", e.response.status_code, url, e.response.text)
            return {"error": str(e), "status_code": e.response.status_code, "detail": e.response.text}
        except Exception as e:
            logger.exception("Unexpected error on %s", url)
            return {"error": str(e)}

    @mcp.tool()
    async def create_volume(
        name: str,
        driver: str = "local",
        labels: str | None = None,
        env_id: str = "0",
        agent_token: str | None = None,
    ) -> Any:
        """Create a new volume. ``labels`` is a comma-separated ``key=value`` list."""
        client = require_client()
        url = await env_path(env_id, "/volumes")
        body: dict[str, Any] = {"name": name, "driver": driver}
        parsed_labels = _labels_to_dict(labels)
        if parsed_labels:
            body["labels"] = parsed_labels
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
        url = await env_path(env_id, f"/volumes/{name}")
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
        name: str,
        force: bool = False,
        env_id: str = "0",
        agent_token: str | None = None,
    ) -> Any:
        """Remove a volume by name. Destructive; requires confirmation token."""
        params = {"force": str(force).lower()}
        token = get_token_store().create(
            action="remove_volume",
            target=f"volume:{name}",
            endpoint=await env_path(env_id, f"/volumes/{name}"),
            method="DELETE",
            params=params,
            classification=ToolClass.DESTRUCTIVE_WRITE,
            env_id=env_id,
            agent_token=agent_token,
        )
        op_hash = compute_operation_hash("remove_volume", f"volume:{name}", None, params)
        return {
            "warning": "Destructive operation. Call confirm_operation(token=...) to proceed.",
            "confirmation_token": token,
            "operation_hash": op_hash,
            "target": f"volume:{name}",
            "action": "remove_volume",
            "classification": ToolClass.DESTRUCTIVE_WRITE,
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
            endpoint=await env_path(env_id, "/volumes/prune"),
            method="POST",
            classification=ToolClass.DESTRUCTIVE_WRITE,
            env_id=env_id,
            agent_token=agent_token,
        )
        op_hash = compute_operation_hash("prune_volumes", "all", None, None)
        return {
            "warning": "Destructive operation. Call confirm_operation(token=...) to proceed.",
            "confirmation_token": token,
            "operation_hash": op_hash,
            "target": "all",
            "action": "prune_volumes",
            "classification": ToolClass.DESTRUCTIVE_WRITE,
        }

    # ── Volume counts & sizes ──────────────────────────────────────────────

    @mcp.tool()
    async def get_volume_counts(env_id: str = "0", agent_token: str | None = None) -> Any:
        """Get volume counts (in use vs total) for the given environment."""
        client = require_client()
        url = await env_path(env_id, "/volumes/counts")
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
        url = await env_path(env_id, "/volumes/sizes")
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
        url = await env_path(env_id, f"/volumes/{name}/usage")
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
        """List all backups for a volume (every page, not just the first 20)."""
        url = await env_path(env_id, f"/volumes/{name}/backups")
        try:
            return await paginate_all(url, agent_token=agent_token)
        except httpx.HTTPStatusError as e:
            logger.warning("HTTP %s on %s: %s", e.response.status_code, url, e.response.text)
            return {"error": str(e), "status_code": e.response.status_code, "detail": e.response.text}
        except Exception as e:
            logger.exception("Unexpected error on %s", url)
            return {"error": str(e)}

    @mcp.tool()
    async def create_volume_backup(name: str, env_id: str = "0", agent_token: str | None = None) -> Any:
        """Create a new backup of a volume. Streams progress; returns the collected log."""
        client = require_client()
        url = await env_path(env_id, f"/volumes/{name}/backups")
        try:
            resp = await client.post(url, headers=_build_headers(agent_token))
            resp.raise_for_status()
            return parse_stream_response(resp)
        except httpx.HTTPStatusError as e:
            logger.warning("HTTP %s on %s: %s", resp.status_code, url, resp.text)
            return {"error": str(e), "status_code": resp.status_code, "detail": resp.text}
        except Exception as e:
            logger.exception("Unexpected error on %s", url)
            return {"error": str(e)}

    @mcp.tool()
    async def restore_volume_backup(
        volume_name: str,
        backup_id: str,
        env_id: str = "0",
        agent_token: str | None = None,
    ) -> Any:
        """Restore a volume backup. Destructive; requires confirmation token."""
        params = {"action": "restore"}
        token = get_token_store().create(
            action="restore_volume_backup",
            target=f"volume:{volume_name}/backup:{backup_id}",
            endpoint=await env_path(env_id, f"/volumes/{volume_name}/backups/{backup_id}"),
            method="POST",
            params=params,
            classification=ToolClass.DESTRUCTIVE_WRITE,
            env_id=env_id,
            agent_token=agent_token,
        )
        op_hash = compute_operation_hash("restore_volume_backup", f"volume:{volume_name}/backup:{backup_id}", None, params)
        return {
            "warning": "Destructive operation. Call confirm_operation(token=...) to proceed.",
            "confirmation_token": token,
            "operation_hash": op_hash,
            "target": f"volume:{volume_name}/backup:{backup_id}",
            "action": "restore_volume_backup",
            "classification": ToolClass.DESTRUCTIVE_WRITE,
        }

    @mcp.tool()
    async def delete_volume_backup(
        backup_id: str,
        env_id: str = "0",
        agent_token: str | None = None,
    ) -> Any:
        """Delete a volume backup. Destructive; requires confirmation token."""
        token = get_token_store().create(
            action="delete_volume_backup",
            target=f"backup:{backup_id}",
            endpoint=await env_path(env_id, f"/volumes/backups/{backup_id}"),
            method="DELETE",
            classification=ToolClass.DESTRUCTIVE_WRITE,
            env_id=env_id,
            agent_token=agent_token,
        )
        op_hash = compute_operation_hash("delete_volume_backup", f"backup:{backup_id}", None, None)
        return {
            "warning": "Destructive operation. Call confirm_operation(token=...) to proceed.",
            "confirmation_token": token,
            "operation_hash": op_hash,
            "target": f"backup:{backup_id}",
            "action": "delete_volume_backup",
            "classification": ToolClass.DESTRUCTIVE_WRITE,
        }

    @mcp.tool()
    async def download_volume_backup(backup_id: str, env_id: str = "0", agent_token: str | None = None) -> Any:
        """Download a volume backup."""
        client = require_client()
        url = await env_path(env_id, f"/volumes/backups/{backup_id}/download")
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

    # ── Volume workspace (read side of the v2 file browser) ────────────────

    @mcp.tool()
    async def browse_volume(
        name: str,
        path: str = "/",
        env_id: str = "0",
        agent_token: str | None = None,
    ) -> Any:
        """List files and directories at a path inside a volume (v3 workspace tree)."""
        client = require_client()
        url = await env_path(env_id, f"/volumes/{name}/workspace")
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
        name: str,
        path: str,
        env_id: str = "0",
        agent_token: str | None = None,
    ) -> Any:
        """Read the contents of a file inside a volume (v3 workspace file)."""
        client = require_client()
        url = await env_path(env_id, f"/volumes/{name}/workspace/file")
        params = {"relativePath": path}
        try:
            resp = await client.get(url, params=params, headers=_build_headers(agent_token))
            resp.raise_for_status()
            result = resp.json()
            return {
                "classification": ToolClass.CREDENTIAL_SENSITIVE,
                "warning": "This response may contain sensitive data (env vars, secrets, config). Handle with care.",
                "data": result,
            }
        except httpx.HTTPStatusError as e:
            logger.warning("HTTP %s on %s: %s", resp.status_code, url, resp.text)
            return {"error": str(e), "status_code": resp.status_code, "detail": resp.text}
        except Exception as e:
            logger.exception("Unexpected error on %s", url)
            return {"error": str(e)}

    @mcp.tool()
    async def create_volume_directory(
        name: str,
        path: str,
        env_id: str = "0",
        agent_token: str | None = None,
    ) -> Any:
        """Not supported on Arcane v3: directory creation needs a workspace manifest."""
        return _unsupported_workspace_write(
            action="create_volume_directory",
            target=f"volume:{name}:{path}",
            alternative=(
                "Directories appear implicitly when a file is written into them. "
                "A future release will send PATCH /volumes/{volumeName}/workspace with a manifest."
            ),
        )

    @mcp.tool()
    async def upload_to_volume(
        name: str,
        path: str,
        content: str,
        env_id: str = "0",
        agent_token: str | None = None,
    ) -> Any:
        """Not supported on Arcane v3: uploads need a workspace manifest plus file parts."""
        return _unsupported_workspace_write(
            action="upload_to_volume",
            target=f"volume:{name}:{path}",
            alternative=(
                "A future release will send PATCH /volumes/{volumeName}/workspace with a "
                "manifest entry and a multipart file part. Use the Arcane UI in the meantime."
            ),
        )

    @mcp.tool()
    async def delete_volume_file(
        name: str,
        path: str,
        env_id: str = "0",
        agent_token: str | None = None,
    ) -> Any:
        """Not supported on Arcane v3: file deletion needs a workspace manifest entry."""
        return _unsupported_workspace_write(
            action="delete_volume_file",
            target=f"volume:{name}:{path}",
            alternative=(
                "A future release will send PATCH /volumes/{volumeName}/workspace with a "
                "delete entry in the manifest. Use the Arcane UI in the meantime."
            ),
        )
