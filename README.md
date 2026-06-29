# opencode-arcane-mcp

An MCP server that exposes [Arcane](https://getarcane.app) Docker management capabilities to AI agents via the Model Context Protocol. Built with FastMCP.

## Install

```bash
pip install opencode-arcane-mcp
# or
uv tool install opencode-arcane-mcp
```

## Configuration

Set these environment variables (or put them in a `.env` file in the working directory):

```env
ARCANE_API_KEY=arc_your_api_key_here
ARCANE_BASE_URL=http://localhost:3552
```

### OpenCode

Add to your `opencode.json`:

```json
{
  "mcp": {
    "arcane-docker": {
      "type": "local",
      "command": ["opencode-arcane-mcp"],
      "env": {
        "ARCANE_API_KEY": "arc_your_key_here",
        "ARCANE_BASE_URL": "http://localhost:3552"
      }
    }
  }
}
```

Or set environment variables globally and omit them from the config.

## Tools (40 total)

### Containers (10)
list_containers, inspect_container, start_container, stop_container, restart_container, remove_container, create_container, exec_in_container, get_container_logs, get_container_stats

### Images (5)
list_images, pull_image, remove_image, inspect_image, tag_image

### Volumes (4)
list_volumes, create_volume, inspect_volume, remove_volume

### Networks (6)
list_networks, create_network, inspect_network, remove_network, connect_container_to_network, disconnect_container_from_network

### Projects / Compose (6)
list_projects, get_project, deploy_project, redeploy_project, remove_project, update_project

### Environments (5)
list_environments, get_environment, create_environment, update_environment, remove_environment

### System (3)
get_docker_info, get_docker_version, prune_system

### Webhooks (1)
trigger_webhook

## Usage

All tools accept `env_id: str = "0"` to target a specific Arcane environment (local Docker is "0", remote agents use UUIDs). Remote agent operations can pass `agent_token: str | None` for authentication.

## Development

```bash
git clone <repo>
cd opencode-arcane-mcp
uv sync
uv run fastmcp run src/opencode_arcane_mcp/server.py
```

## Publishing

```bash
uv build
uv publish
```

## License

MIT
