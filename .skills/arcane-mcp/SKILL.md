---
name: arcane-mcp
description: >
  MCP server that exposes the Arcane Docker management API to AI agents.
  123 tools across 13 modules — containers, images, volumes, networks,
  Compose projects, registries, vulnerability scanning, webhooks, system,
  updater, environments, ports, and activities/events.
  Built with FastMCP (Python), managed with UV.
  Triggers: working with Docker via Arcane API, managing containers/images/volumes,
  deploying Compose projects, interacting with the arcane-mcp MCP server.
---

# Arcane MCP — Docker Management for AI Agents

Arcane MCP is a Python MCP server that exposes the [Arcane](https://getarcane.app) Docker management API via the Model Context Protocol. Any MCP-compatible agent (OpenCode, Claude, Cursor) can use it to manage Docker.

## Stack

- **MCP Framework:** FastMCP ≥3.3.1
- **HTTP Client:** httpx (async, lazy client via `client.py`)
- **Env Loading:** python-dotenv (loaded at import)
- **Package Manager:** UV
- **Python:** ≥3.11

## Architecture

```
AI Agent → Arcane MCP (FastMCP) → Arcane API → Docker
```

Each tool category lives in its own file under `tools/`, exporting a `register(mcp: FastMCP)` function. `server.py` imports and calls all register functions.

The HTTP client is lazy — created on first tool call, not at import. Reads `ARCANE_BASE_URL` and `ARCANE_API_KEY` from the environment or `.env`.

## Tool Categories (123 tools, 13 modules)

| Module | Tools | Description |
|--------|-------|-------------|
| **Containers** | 18 | Full lifecycle: list, inspect, create, start, stop, restart, kill, pause, unpause, remove, redeploy, commit, update, exec, logs, stats, auto-update, counts |
| **Images** | 19 | Pull, remove, tag, prune, build, search, upload, history, export, attestations, vulnerability scan, updates |
| **Volumes** | 18 | Create, inspect, remove, prune, backup/restore, browse files, read/write, create dirs |
| **Networks** | 9 | Create, inspect, remove, connect/disconnect, prune, topology, counts |
| **Projects** | 17 | Deploy, update, remove, down, restart, build, archive, unarchive, pull images, compose, file, runtime, counts |
| **System** | 9 | Docker info/version, prune, health, upgrade, bulk container start/stop |
| **Environments** | 5 | List, get, create, update, remove Arcane environments |
| **Registries** | 6 | List, create, get, update, delete, test container registries |
| **Webhooks** | 5 | Trigger, list, create, update, delete webhooks |
| **Activities** | 7 | List/cancel activities, browse events, clear history |
| **Vulnerabilities** | 6 | Summary, list all, ignore/unignore, scanner status |
| **Updater** | 3 | Run, status, history |
| **Ports** | 1 | List all port mappings |

## Key Conventions

Every tool follows these patterns:

- **`env_id: str = "0"`** — targets a specific Arcane environment (local Docker is "0", remote agents use UUIDs)
- **`agent_token: str | None = None`** — optional auth for remote agent operations, sent as `X-Arcane-Agent-Token` header
- **Error handling** — always returns a dict, never raises. Caught exceptions return `{"error": "...", "status_code": ..., "detail": "..."}`
- **Destructive safety** — tools that remove, prune, kill, restore, or overwrite require `confirm: bool = False`. Without it they return a warning dict:
  ```python
  {"warning": "Destructive operation. Set confirm=True to proceed.", "target": "..."}
  ```

## Quick Commands

```bash
uv sync                                    # Install deps
uv run python -m arcane_mcp.server  # Run MCP server
uv run fastmcp dev src/arcane_mcp/server.py  # Dev mode w/ browser inspector
uv build                                   # Build wheel
```

## Configuration

Environment variables (or `.env` file):

```env
ARCANE_API_KEY=arc_your_key_here
ARCANE_BASE_URL=http://localhost:3552
```

OpenCode config:

```json
{
  "mcp": {
    "arcane-docker": {
      "type": "local",
      "command": ["arcane-mcp"],
      "env": {
        "ARCANE_API_KEY": "arc_your_key_here",
        "ARCANE_BASE_URL": "http://localhost:3552"
      }
    }
  }
}
```

## Source

Repo: `https://github.com/splaq/arcane-mcp` (also on Forgejo at `fj.splaq.us/splaq/arcane-mcp`)

## Related Skills

- **arcane** (`~/.agents/skills/arcane/`) — the Arcane application itself (Docker management UI, not the MCP server). Use that skill for questions about the Arcane UI, dashboards, SSO config, GitOps, etc. This skill is for the MCP server only.
