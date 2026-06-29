# AGENTS.md — Arcane MCP Server

MCP server that exposes the [Arcane API](https://getarcane.app/api-reference) to AI agents.
Built with **FastMCP (Python)** and managed with **UV**.

**Status:** Active development. 123 tools across 13 categories covering all major Arcane API endpoints.

---

## Stack

- **MCP Framework:** FastMCP ≥3.3.1
- **HTTP Client:** httpx (async, lazy client via `client.py`)
- **Env Loading:** python-dotenv (loaded at import in `client.py`)
- **Package Manager:** UV (`uv add`, `uv run`, `uv sync`)
- **Python:** 3.11 (`.python-version`, `>=3.11` in `pyproject.toml`)
- **Build:** hatchling
- **Memory:** GrayMatter hivemind (per-project: `arcane-mcp-<role>`)

---

## Quick Commands

```bash
uv sync                                            # Install deps
uv run python -m opencode_arcane_mcp.server        # Run the MCP server (stdio)
uv run fastmcp run src/opencode_arcane_mcp/server.py  # Same, via FastMCP CLI
uv run fastmcp dev src/opencode_arcane_mcp/server.py   # Dev mode with inspector (browser UI)
uv build                                            # Build wheel
uv publish                                          # Push to PyPI
```

**Note:** No lint/typecheck config exists yet. No test suite either — run `uv run` directly for ad-hoc verification.

---

## Architecture

### Module pattern (NOT global client)

Each tool category is a separate file in `tools/` exporting a `register(mcp: FastMCP) -> None` function.
`server.py` imports and calls all `register()` functions.

### Client pattern (lazy, env-gated)

`client.py` provides `require_client()` — it lazily creates an `httpx.AsyncClient` from env vars and caches it.
If `ARCANE_BASE_URL` or `ARCANE_API_KEY` is missing, `require_client()` raises at tool-call time, not at import.

```python
# client.py — never create httpx.AsyncClient at module level
def require_client() -> httpx.AsyncClient:
    # reads ARCANE_BASE_URL + ARCANE_API_KEY from dotenv
    # returns cached AsyncClient with X-Api-Key header
```

### Tool pattern

```python
from fastmcp import FastMCP
from ..client import require_client, _build_headers

def register(mcp: FastMCP) -> None:
    @mcp.tool()
    async def my_tool(arg: str, env_id: str = "0", agent_token: str | None = None) -> Any:
        """Tool docstring becomes MCP tool description."""
        client = require_client()
        try:
            resp = await client.get(f"/api/environments/{env_id}/...", headers=_build_headers(agent_token))
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            return {"error": str(e), "status_code": resp.status_code, "detail": resp.text}
        except Exception as e:
            return {"error": str(e)}
```

### Key conventions

- **`env_id: str = "0"`** on every resource tool (string, NOT int — the API uses UUIDs for remote agents)
- **`agent_token: str | None = None`** on every resource tool (passed as `X-Arcane-Agent-Token` header for remote agent auth)
- **Error handling:** always return a dict, never raise. Use the httpx exception block pattern above.
- **Destructive tools** (`remove_*`, `prune_*`) require `confirm: bool = False` — gate on it, return warning dict.

---

## Actual Project Structure

```
src/opencode_arcane_mcp/
├── __init__.py
├── server.py              # FastMCP entrypoint — calls all register() functions
├── client.py              # Lazy httpx client factory + _build_headers helper
└── tools/
    ├── __init__.py
    ├── activities.py      # 7 tools: list_activities, get_activity, cancel_activity, clear_activity_history, list_events, get_environment_events, delete_event
    ├── containers.py      # 18 tools: list, inspect, create, start, stop, restart, kill, pause, unpause, remove, redeploy, commit, update, exec, logs, stats, set_auto_update, counts
    ├── environments.py    # 5 tools: list, get, create, update, remove
    ├── images.py          # 19 tools: list, inspect, pull, remove, tag, prune, counts, build, search, upload, history, export, attestations, scan_vulns, get_vulns, vuln_summary, check_update, check_all_updates, update_summary
    ├── networks.py        # 9 tools: list, create, inspect, remove, connect, disconnect, prune, counts, topology
    ├── ports.py           # 1 tool: list_ports
    ├── projects.py        # 17 tools: list, get, deploy, redeploy, update, remove, counts, down, restart, build, archive, unarchive, pull_images, compose, file, update_services, runtime
    ├── registries.py      # 6 tools: list, create, get, update, delete, test
    ├── system.py          # 9 tools: get_docker_info, get_docker_version, prune_system, health, check_upgrade, trigger_upgrade, start_all, start_stopped, stop_all
    ├── updater.py         # 3 tools: run, status, history
    ├── volumes.py         # 18 tools: list, create, inspect, remove, prune, counts, sizes, usage, list_backups, create_backup, restore_backup, delete_backup, download_backup, browse, read_file, create_dir, upload, delete_file
    ├── vulnerabilities.py # 6 tools: summary_all, list_all, ignore, list_ignored, unignore, scanner_status
    └── webhooks.py        # 5 tools: trigger, list, create, update, delete
```

---

## Environment & Auth

- `.env` holds `ARCANE_API_KEY` and `ARCANE_BASE_URL` — already in `.gitignore`
- Auth via `X-Api-Key` header (NOT Bearer token), added at client construction
- Remote agents send `X-Arcane-Agent-Token` header via `_build_headers(agent_token)`
- Default Arcane port: 3552 (`http://localhost:3552`)
- API is multi-tenant: `/api/environments/{env_id}/{resource}`
- Environment "0" = default local. Remote agents use UUIDs.
- Interactive API docs live **in the Arcane UI** at Settings → API Keys → API Reference
- Arcane CLI: `arcane-cli config set` for reference

---

## Arcane API Key Endpoints

Base: `/api/environments/{env_id}`

| Resource | Endpoints |
|----------|-----------|
| Containers | GET `/containers`, GET `/containers/{id}`, POST `/containers`, POST `/containers/{id}/start\|stop\|restart\|kill\|pause\|unpause\|redeploy\|commit\|update`, DELETE `/containers/{id}`, PUT `/containers/{id}/auto-update` |
| Images | GET `/images`, GET `/images/{id}`, POST `/images/pull\|prune\|build\|search\|upload`, DELETE `/images/{id}`, POST `/images/{name}/tag`, GET `/images/{name}/history\|export\|attestations` |
| Volumes | GET `/volumes`, GET `/volumes/{name}`, POST `/volumes\|prune`, DELETE `/volumes/{name}`, GET/POST `/volumes/{name}/browse` (full file browser), POST `/volumes/{name}/backups` |
| Networks | GET `/networks`, GET `/networks/{id}`, POST `/networks\|prune`, DELETE `/networks/{id}`, POST `/networks/{id}/connect\|disconnect` |
| Projects | GET `/projects`, GET `/projects/{id}`, POST `/projects`, PUT `/projects/{id}`, DELETE `/projects/{id}`, POST `/projects/{id}/up\|down\|restart\|redeploy\|build\|archive\|unarchive\|destroy` |
| System | GET `/system/docker/info`, POST `/system/prune`, GET `/version`, POST `/system/containers/start-all\|start-stopped\|stop-all`, GET/POST `/system/upgrade` |
| Environments | GET `/environments`, GET `/environments/{id}`, POST `/environments`, PUT `/environments/{id}`, DELETE `/environments/{id}` |
| Webhooks | POST `/api/webhooks/trigger/{token}` (env-independent, token is in URL) |

---

## Destructive Operations — Safety Pattern

Any tool that removes, prunes, force-stops, or overwrites must:

1. Accept `confirm: bool = False` parameter
2. Return `{"warning": "...", "target": ...}` dict if `confirm=False`
3. Gate the real operation behind `if not confirm: return warning_dict`

Example from `containers.py`:
```python
async def remove_container(container_id: str, force: bool = False,
                           env_id: str = "0", agent_token: str | None = None,
                           confirm: bool = False) -> Any:
    if not confirm:
        return {"warning": "Destructive operation. Set confirm=True to remove this container.",
                "container_id": container_id}
```

---

## Security

- `.env` must stay gitignored (already is)
- Auth via `X-Api-Key` — never expose in URLs, return values, or logs
- `exec_in_container` is high-privilege — returns API-gap notice (Arcane API doesn't expose exec). Use SSH workaround.
- `ARCANE_API_KEY` is a secret; treat it like a password

---

## GrayMatter Memory

Use per-project agent ID `arcane-mcp-<role>` (e.g. `arcane-mcp-orchestrator`, `arcane-mcp-fixer`).

Useful memory keys:
- `arcane.containers.recent` — recently inspected container IDs
- `arcane.preferences.log_tail` — default log tail lines
- `arcane.preferences.default_env_id` — default environment ID (usually "0")
- `arcane.history.destructive` — `{action, target, timestamp}` logs

**Read before:** listing containers, destructive operations
**Write after:** destructive ops, preference changes, container inspections by name

---

## Naming Conventions

- Tool names: `snake_case`, verb-first (`list_`, `get_`, `create_`, `remove_`, `start_`, `stop_`)
- Keep docstrings concise — they become MCP tool descriptions in the schema
