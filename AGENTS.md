# AGENTS.md — Arcane MCP Server

MCP server that exposes the [Arcane API](https://getarcane.app/api-reference) to AI agents.
Built with **FastMCP (Python)** and managed with **UV**.

**Status:** Active development. 127 tools across 14 categories covering all major Arcane API endpoints.

---

## Stack

- **MCP Framework:** FastMCP ≥3.3.1
- **HTTP Client:** httpx (async, lazy client via `client.py`)
- **Env Loading:** python-dotenv (loaded at import in `client.py`)
- **Package Manager:** UV (`uv add`, `uv run`, `uv sync`)
- **Python:** 3.11 (`.python-version`, `>=3.11` in `pyproject.toml`)
- **Build:** hatchling
- **Memory:** Hivemind (per-project: `arcane-mcp-<role>`)

---

## Quick Commands

```bash
uv sync                                            # Install deps
uv run python -m arcane_mcp.server        # Run the MCP server (stdio)
uv run fastmcp run src/arcane_mcp/server.py  # Same, via FastMCP CLI
uv run fastmcp dev src/arcane_mcp/server.py   # Dev mode with inspector (browser UI)
uv build                                            # Build wheel
uv publish                                          # Push to PyPI
```

**Note:** ruff and mypy are configured in `pyproject.toml`; the suite runs with `uv run pytest`.
`ARCANE_API_VERSION=2` is pinned by `tests/conftest.py` so route tests stay off the network.

---

## Releasing — two repos must agree

The code lives in **GitHub** (`MikeCase/arcane-mcp`); the landing page lives in **Forgejo**
(`fj.splaq.us/splaq/arcane-mcp-site`) and is served at <https://arcanemcp.splaq.us>. Nothing links
them, so a release means touching both or the page quietly lies about the version.

1. **Code repo** — bump `pyproject.toml` `version`, add a `CHANGELOG.md` entry, commit, push to
   `origin` (GitHub).
2. **Count the tools** (only when tools were added or removed):
   ```bash
   grep -rh '@mcp.tool()' src/arcane_mcp/tools/*.py | wc -l
   ```
3. **Site repo** — clone `git@fj.splaq.us:splaq/arcane-mcp-site.git`, then update three places in
   `index.html`: the hero badge, the stats block (`stat-number`), and the architecture caption
   (`<div class="desc">`). Commit and push to `main`.
4. **Verify** — Arcane's GitOps sync publishes within ~5 minutes:
   ```bash
   curl -s https://arcanemcp.splaq.us | grep -o 'v[0-9.]* &middot; [0-9]* tools'
   ```

Skipping step 3 is how the badge sat at `v0.3.0 · 125 tools` while the server was `0.4.0` with 127.

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
from ..client import env_path, require_client, _build_headers

def register(mcp: FastMCP) -> None:
    @mcp.tool()
    async def my_tool(arg: str, env_id: str = "0", agent_token: str | None = None) -> Any:
        """Tool docstring becomes MCP tool description."""
        client = require_client()
        try:
            url = await env_path(env_id, "/some/resource")
            resp = await client.get(url, headers=_build_headers(agent_token))
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            return {"error": str(e), "status_code": resp.status_code, "detail": resp.text}
        except Exception as e:
            return {"error": str(e)}
```

**Never hardcode `/api/environments/{env_id}`.** Build every route with `env_path(env_id, suffix)`
(or `api_collection()` for the environment collection, which has no `env_id`). See
"API version detection" below for why.

### Key conventions

- **`env_id: str = "0"`** on every resource tool (string, NOT int — the API uses UUIDs for remote agents)
- **`agent_token: str | None = None`** on every resource tool (passed as `X-Arcane-Agent-Token` header for remote agent auth)
- **Error handling:** always return a dict, never raise. Use the httpx exception block pattern above.
- **Destructive tools** (`remove_*`, `prune_*`) use a three-layer safety system: confirmation tokens (two-step handshake via `confirm_operation()`), dry-run default on prune tools, and structured audit logging to `~/.arcane-mcp-audit.log`.

---

## Actual Project Structure

```
src/arcane_mcp/
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
- API is multi-tenant: `/api/environments/{env_id}/{resource}` on **v2**, `/api/agents/{env_id}/{resource}` on **v3+**
- Environment "0" = default local. Remote agents use UUIDs.
- Interactive API docs live **in the Arcane UI** at Settings → API Keys → API Reference
- The full OpenAPI spec is served at `GET /api/openapi.json` — the fastest way to settle any
  contract question (field names, content types, method). Do not guess at payload shapes.

### API version detection

Arcane **v3.0.0** renamed the routes (`/api/environments` → `/api/agents`, PR #4731) and switched
project update from `PUT` to `PATCH`. `client.py` detects the major version once per process from
`GET /api/version` and exposes:

| Helper | Returns |
|---|---|
| `await detect_api_version()` | `2` or `3`; cached; never raises (falls back to 2, uncached) |
| `await api_prefix(env_id)` | `/api/agents/{env_id}` on v3, else `/api/environments/{env_id}` |
| `await api_collection()` | `/api/agents` on v3, else `/api/environments` (no `env_id`) |
| `await env_path(env_id, suffix)` | `api_prefix(env_id) + suffix` |

`ARCANE_API_VERSION` overrides detection (`"2"`, `"3"`, `"v3.1.0"`) and makes no HTTP call — that is
also how the test suite keeps route tests off the network. Resolve endpoints at **proposal time**
when storing them on a confirmation token, so the token carries the fully-qualified path.

---

## Arcane API Key Endpoints

Base: `/api/environments/{env_id}` on v2, `/api/agents/{env_id}` on v3 — always build routes with `env_path()`. The full spec is at `GET /api/openapi.json`.

| Resource | Endpoints |
|----------|-----------|
| Containers | GET `/containers`, GET `/containers/{id}`, POST `/containers`, POST `/containers/{id}/start\|stop\|restart\|kill\|pause\|unpause\|redeploy\|commit\|update`, DELETE `/containers/{id}`, PUT `/containers/{id}/auto-update` |
| Images | GET `/images`, GET `/images/{id}`, POST `/images/pull\|prune\|build\|search\|upload`, DELETE `/images/{id}`, POST `/images/{name}/tag`, GET `/images/{name}/history\|export\|attestations` |
| Volumes | GET `/volumes`, GET `/volumes/{name}`, POST `/volumes\|prune`, DELETE `/volumes/{name}`, GET/POST `/volumes/{name}/browse` (full file browser), POST `/volumes/{name}/backups` |
| Networks | GET `/networks`, GET `/networks/{id}`, POST `/networks\|prune`, DELETE `/networks/{id}`, POST `/networks/{id}/connect\|disconnect` |
| Projects | GET `/projects`, GET `/projects/{id}`, **POST `/projects` (multipart — see below)**, PUT `/projects/{id}` on v2 / **PATCH** on v3 (JSON), DELETE `/projects/{id}`, POST `/projects/{id}/up\|down\|restart\|redeploy\|build\|archive\|unarchive\|destroy` |
| System | GET `/system/docker/info`, POST `/system/prune`, GET `/version`, POST `/system/containers/start-all\|start-stopped\|stop-all`, GET/POST `/system/upgrade` |
| Environments | GET `/environments`, GET `/environments/{id}`, POST `/environments`, PUT `/environments/{id}`, DELETE `/environments/{id}` — v3 calls these `/agents` (`api_collection()`) |
| Webhooks | POST `/api/webhooks/trigger/{token}` (env-independent, token is in URL) |

### Project create is multipart-only

`POST /projects` has taken **`multipart/form-data`** since Arcane v2.8.0, and there is no JSON
variant (a JSON body returns `422 cannot read multipart form`). Two mandatory text parts, exactly
one each:

| Part | Content |
|---|---|
| `project` | JSON string: `{"name": "...", "composeContent": "<compose yaml>", "envContent"?, "directory"?, "tags"?}` |
| `manifest` | JSON string workspace manifest; send `{"fileChanges": []}` for a plain create |

The compose text lives in `composeContent` **inside the `project` part** — there is no top-level
`compose` field on any version. Optional `files` parts are real uploads referenced by
`manifest.fileChanges[].uploadIndex`. Success is `200`, not `201`.

Confirmation tokens carry an `encoding` (`"json"` or `"multipart"`) so `confirm_operation()` replays
the body correctly; `multipart` bodies must be a flat `dict[str, str]`.


---

## Destructive Operations — Safety Pattern

Any tool that removes, prunes, force-stops, or overwrites must:

Destructive and high-risk writes do **not** execute on call. They propose, then require a second call.

1. The tool builds the operation and calls `get_token_store().create(...)` with the action, target,
   fully-resolved endpoint (see `env_path`), method, body, `encoding`, and classification.
2. It returns a proposal dict: `confirmation_token`, `operation_hash`, `classification`,
   `risk_level`, `warning`, `target`, `action` — and, for compose, a parsed plan. Nothing is sent.
3. The caller then invokes `confirm_operation(token=..., operation_hash=...)`, which consumes the
   token, re-checks the resource hash, replays the request, and writes three audit events.

Example shape from `containers.py`:
```python
token = get_token_store().create(
    action="remove_container",
    target=container_id,
    endpoint=await env_path(env_id, f"/containers/{container_id}"),
    method="DELETE",
    body=None, params=None,
    classification=ToolClass.DESTRUCTIVE_WRITE,
    env_id=env_id, agent_token=agent_token,
)
return {"warning": "...", "confirmation_token": token,
        "operation_hash": compute_operation_hash("remove_container", container_id, None, None), ...}
```

Tokens live in memory, expire after 120 s, and are bound to the operation hash (which covers action,
target, body and params) — changing any argument invalidates the token.

---

## Security

- `.env` must stay gitignored (already is)
- Auth via `X-Api-Key` — never expose in URLs, return values, or logs
- `exec_in_container` is high-privilege — returns API-gap notice (Arcane API doesn't expose exec). Use SSH workaround.
- `ARCANE_API_KEY` is a secret; treat it like a password

---

## Hivemind Memory

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
