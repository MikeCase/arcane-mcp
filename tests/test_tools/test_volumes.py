"""Tests for volume tools against the Arcane v3 routes."""

from __future__ import annotations

import json
from typing import Any

import pytest

from tests.conftest import call_tool, register_operations

BASE = "http://localhost:3552/api/agents/0/volumes"


@pytest.fixture
def ops_mcp(mcp: Any) -> Any:
    """MCP instance with the safety tools registered (for confirm_operation)."""
    return register_operations(mcp)


def _envelope(items: list[dict[str, Any]], has_next: bool = False) -> dict[str, Any]:
    return {
        "data": items,
        "pagination": {"hasNextPage": has_next, "totalItems": len(items)},
        "success": True,
    }


@pytest.mark.asyncio
async def test_list_volumes(mcp: Any, httpx_mock: Any) -> None:
    """list_volumes walks the paginated collection and returns the merged envelope."""
    httpx_mock.add_response(
        url=BASE,
        method="GET",
        match_params={"start": "0", "limit": "100"},
        json=_envelope([{"name": "data-vol", "driver": "local"}]),
    )
    result = await call_tool(mcp, "list_volumes")
    assert result["data"] == [{"name": "data-vol", "driver": "local"}]

    request = httpx_mock.get_requests()[0]
    assert request.url.path == "/api/agents/0/volumes"
    assert request.url.params["start"] == "0"
    assert request.url.params["limit"] == "100"


@pytest.mark.asyncio
async def test_list_volumes_follows_pages(mcp: Any, httpx_mock: Any) -> None:
    """list_volumes keeps requesting while pagination.hasNextPage is true."""
    httpx_mock.add_response(
        url=BASE,
        method="GET",
        match_params={"start": "0", "limit": "100"},
        json=_envelope([{"name": "vol-1"}], has_next=True),
    )
    httpx_mock.add_response(
        url=BASE,
        method="GET",
        match_params={"start": "1", "limit": "100"},
        json=_envelope([{"name": "vol-2"}], has_next=False),
    )
    result = await call_tool(mcp, "list_volumes")
    assert [v["name"] for v in result["data"]] == ["vol-1", "vol-2"]

    requests = httpx_mock.get_requests()
    assert len(requests) == 2
    assert requests[1].url.params["start"] == "1"


@pytest.mark.asyncio
async def test_create_volume(mcp: Any, httpx_mock: Any) -> None:
    """create_volume posts name, driver and labels as a map."""
    httpx_mock.add_response(
        url=BASE,
        method="POST",
        json={"name": "my-vol", "driver": "local"},
    )
    result = await call_tool(mcp, "create_volume", name="my-vol", labels="tier=db,owner=mike")
    assert result["name"] == "my-vol"

    body = json.loads(httpx_mock.get_requests()[0].content)
    assert body == {"name": "my-vol", "driver": "local", "labels": {"tier": "db", "owner": "mike"}}


@pytest.mark.asyncio
async def test_inspect_volume(mcp: Any, httpx_mock: Any) -> None:
    """inspect_volume returns volume details."""
    httpx_mock.add_response(
        url=f"{BASE}/my-vol",
        method="GET",
        json={"name": "my-vol", "mountpoint": "/data"},
    )
    result = await call_tool(mcp, "inspect_volume", name="my-vol")
    assert result["mountpoint"] == "/data"


@pytest.mark.asyncio
async def test_remove_volume_needs_confirm(mcp: Any, httpx_mock: Any) -> None:
    """remove_volume returns a proposal and touches no endpoint."""
    result = await call_tool(mcp, "remove_volume", name="my-vol")
    assert result["action"] == "remove_volume"
    assert result["target"] == "volume:my-vol"
    assert result["classification"] == "destructive_write"
    assert result["confirmation_token"]
    assert result["operation_hash"]
    assert "warning" in result
    assert httpx_mock.get_requests() == []


@pytest.mark.asyncio
async def test_remove_volume_confirmed(ops_mcp: Any, httpx_mock: Any) -> None:
    """remove_volume sends force as a query parameter after confirm_operation."""
    httpx_mock.add_response(
        url=f"{BASE}/my-vol",
        method="DELETE",
        match_params={"force": "false"},
        json={"message": "removed"},
    )
    proposal = await call_tool(ops_mcp, "remove_volume", name="my-vol")
    assert httpx_mock.get_requests() == []

    result = await call_tool(
        ops_mcp,
        "confirm_operation",
        token=proposal["confirmation_token"],
        operation_hash=proposal["operation_hash"],
    )
    assert result == {"message": "removed"}

    request = httpx_mock.get_requests()[0]
    assert request.method == "DELETE"
    assert request.url.path == "/api/agents/0/volumes/my-vol"
    assert request.url.params["force"] == "false"
    assert request.content == b""


@pytest.mark.asyncio
async def test_remove_volume_force_param(ops_mcp: Any, httpx_mock: Any) -> None:
    """force=True travels as ?force=true."""
    httpx_mock.add_response(
        url=f"{BASE}/my-vol",
        method="DELETE",
        match_params={"force": "true"},
        json={"message": "removed"},
    )
    proposal = await call_tool(ops_mcp, "remove_volume", name="my-vol", force=True)
    await call_tool(
        ops_mcp,
        "confirm_operation",
        token=proposal["confirmation_token"],
        operation_hash=proposal["operation_hash"],
    )
    assert httpx_mock.get_requests()[0].url.params["force"] == "true"


@pytest.mark.asyncio
async def test_prune_volumes_dry_run(mcp: Any, httpx_mock: Any) -> None:
    """prune_volumes defaults to a dry run and sends nothing."""
    result = await call_tool(mcp, "prune_volumes")
    assert result["dry_run"] is True
    assert httpx_mock.get_requests() == []


@pytest.mark.asyncio
async def test_prune_volumes_proposal(mcp: Any, httpx_mock: Any) -> None:
    """prune_volumes with dry_run=False proposes POST /volumes/prune."""
    result = await call_tool(mcp, "prune_volumes", dry_run=False)
    assert result["confirmation_token"]
    assert httpx_mock.get_requests() == []


@pytest.mark.asyncio
async def test_volume_counts_and_sizes(mcp: Any, httpx_mock: Any) -> None:
    """Counts and sizes read their own v3 sub-paths."""
    httpx_mock.add_response(url=f"{BASE}/counts", method="GET", json={"inUse": 2, "total": 5})
    httpx_mock.add_response(url=f"{BASE}/sizes", method="GET", json={"data": []})

    assert await call_tool(mcp, "get_volume_counts") == {"inUse": 2, "total": 5}
    assert await call_tool(mcp, "get_volume_sizes") == {"data": []}


@pytest.mark.asyncio
async def test_get_volume_usage(mcp: Any, httpx_mock: Any) -> None:
    """get_volume_usage reads /volumes/{name}/usage."""
    httpx_mock.add_response(url=f"{BASE}/data-vol/usage", method="GET", json={"size": 4096})
    assert await call_tool(mcp, "get_volume_usage", name="data-vol") == {"size": 4096}


@pytest.mark.asyncio
async def test_list_volume_backups(mcp: Any, httpx_mock: Any) -> None:
    """list_volume_backups paginates /volumes/{name}/backups."""
    httpx_mock.add_response(
        url=f"{BASE}/data-vol/backups",
        method="GET",
        match_params={"start": "0", "limit": "100"},
        json=_envelope([{"id": "b1"}]),
    )
    result = await call_tool(mcp, "list_volume_backups", name="data-vol")
    assert result["data"] == [{"id": "b1"}]

    request = httpx_mock.get_requests()[0]
    assert request.url.path == "/api/agents/0/volumes/data-vol/backups"
    assert request.url.params["limit"] == "100"


@pytest.mark.asyncio
async def test_create_volume_backup_parses_stream(mcp: Any, httpx_mock: Any) -> None:
    """create_volume_backup reads the streamed action log instead of json()."""
    body = "\n".join(
        [
            '{"activityId":"act-1","type":"activity"}',
            '{"log":"backing up"}',
            '{"done":true}',
        ]
    )
    httpx_mock.add_response(
        url=f"{BASE}/data-vol/backups",
        method="POST",
        status_code=202,
        content=body.encode(),
        headers={"content-type": "application/x-json-stream"},
    )
    result = await call_tool(mcp, "create_volume_backup", name="data-vol")
    assert result["activityId"] == "act-1"
    assert result["logs"] == ["backing up"]
    assert result["done"] is True


@pytest.mark.asyncio
async def test_restore_volume_backup_needs_confirm(mcp: Any, httpx_mock: Any) -> None:
    """restore_volume_backup proposes and sends nothing."""
    result = await call_tool(mcp, "restore_volume_backup", volume_name="data-vol", backup_id="b1")
    assert result["action"] == "restore_volume_backup"
    assert result["target"] == "volume:data-vol/backup:b1"
    assert httpx_mock.get_requests() == []


@pytest.mark.asyncio
async def test_restore_volume_backup_confirmed(ops_mcp: Any, httpx_mock: Any) -> None:
    """restore_volume_backup posts to /backups/{id}?action=restore on v3."""
    httpx_mock.add_response(
        url=f"{BASE}/data-vol/backups/b1",
        method="POST",
        match_params={"action": "restore"},
        json={"message": "restored"},
    )
    proposal = await call_tool(ops_mcp, "restore_volume_backup", volume_name="data-vol", backup_id="b1")
    result = await call_tool(
        ops_mcp,
        "confirm_operation",
        token=proposal["confirmation_token"],
        operation_hash=proposal["operation_hash"],
    )
    assert result == {"message": "restored"}

    request = httpx_mock.get_requests()[0]
    assert request.method == "POST"
    assert request.url.path == "/api/agents/0/volumes/data-vol/backups/b1"
    assert request.url.params["action"] == "restore"


@pytest.mark.asyncio
async def test_delete_volume_backup_confirmed(ops_mcp: Any, httpx_mock: Any) -> None:
    """delete_volume_backup deletes /volumes/backups/{id}."""
    httpx_mock.add_response(
        url=f"{BASE}/backups/b9",
        method="DELETE",
        json={"message": "deleted"},
    )
    proposal = await call_tool(ops_mcp, "delete_volume_backup", backup_id="b9")
    result = await call_tool(
        ops_mcp,
        "confirm_operation",
        token=proposal["confirmation_token"],
        operation_hash=proposal["operation_hash"],
    )
    assert result == {"message": "deleted"}
    assert httpx_mock.get_requests()[0].url.path == "/api/agents/0/volumes/backups/b9"


@pytest.mark.asyncio
async def test_download_volume_backup(mcp: Any, httpx_mock: Any) -> None:
    """download_volume_backup reads /volumes/backups/{id}/download."""
    httpx_mock.add_response(
        url=f"{BASE}/backups/b9/download",
        method="GET",
        json={"url": "http://example/backup.tar.gz"},
    )
    assert await call_tool(mcp, "download_volume_backup", backup_id="b9") == {"url": "http://example/backup.tar.gz"}


@pytest.mark.asyncio
async def test_browse_volume_uses_workspace(mcp: Any, httpx_mock: Any) -> None:
    """browse_volume reads the v3 workspace tree with a path query."""
    httpx_mock.add_response(
        url=f"{BASE}/data-vol/workspace",
        method="GET",
        match_params={"path": "/etc"},
        json={"success": True, "data": {"files": [{"name": "app.yml"}]}},
    )
    result = await call_tool(mcp, "browse_volume", name="data-vol", path="/etc")
    assert result["data"]["files"] == [{"name": "app.yml"}]

    request = httpx_mock.get_requests()[0]
    assert request.url.path == "/api/agents/0/volumes/data-vol/workspace"
    assert request.url.params["path"] == "/etc"


@pytest.mark.asyncio
async def test_read_volume_file_uses_workspace_file(mcp: Any, httpx_mock: Any) -> None:
    """read_volume_file reads /workspace/file with a relativePath query."""
    httpx_mock.add_response(
        url=f"{BASE}/data-vol/workspace/file",
        method="GET",
        match_params={"relativePath": "notes.txt"},
        json={"success": True, "data": {"content": "hello", "relativePath": "notes.txt"}},
    )
    result = await call_tool(mcp, "read_volume_file", name="data-vol", path="notes.txt")
    assert result["classification"] == "credential_sensitive"
    assert result["data"]["data"]["content"] == "hello"

    request = httpx_mock.get_requests()[0]
    assert request.url.path == "/api/agents/0/volumes/data-vol/workspace/file"
    assert request.url.params["relativePath"] == "notes.txt"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("tool", "kwargs"),
    [
        ("create_volume_directory", {"name": "data-vol", "path": "newdir"}),
        ("upload_to_volume", {"name": "data-vol", "path": "notes.txt", "content": "hi"}),
        ("delete_volume_file", {"name": "data-vol", "path": "notes.txt"}),
    ],
)
async def test_workspace_writes_unsupported_send_no_request(mcp: Any, httpx_mock: Any, tool: str, kwargs: dict[str, Any]) -> None:
    """The v3 workspace-manifest writes answer 'not supported' without HTTP."""
    result = await call_tool(mcp, tool, **kwargs)
    assert result["error"] == "not_supported"
    assert result["supported"] is False
    assert result["action"] == tool
    assert "manifest" in result["reason"]
    assert "warning" in result
    assert "confirmation_token" not in result
    assert httpx_mock.get_requests() == []
