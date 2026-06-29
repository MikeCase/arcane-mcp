# opencode-arcane-mcp

An MCP server that exposes [Arcane](https://getarcane.app) Docker management capabilities to AI agents via the Model Context Protocol. Built with FastMCP.

Covers the core Docker management API: containers, images, volumes, networks, Compose projects, registries, vulnerability scanning, port mappings, webhooks, system management, updater, activities/events, and environment management.

**123 tools across 13 modules.**

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

## Tools (123 total)

### Containers (18)
list_containers, inspect_container, create_container, start_container, stop_container, restart_container, kill_container, pause_container, unpause_container, remove_container, redeploy_container, commit_container, update_container, set_container_auto_update, exec_in_container, get_container_logs, get_container_stats, get_container_counts

### Images (19)
list_images, inspect_image, pull_image, remove_image, tag_image, prune_images, get_image_counts, build_image, search_images, upload_image, get_image_history, get_image_export, get_image_attestations, scan_image_vulnerabilities, get_image_vulnerabilities, get_vulnerability_summary, check_image_update, check_all_image_updates, get_image_update_summary

### Volumes (18)
list_volumes, create_volume, inspect_volume, remove_volume, prune_volumes, get_volume_counts, get_volume_sizes, get_volume_usage, list_volume_backups, create_volume_backup, restore_volume_backup, delete_volume_backup, download_volume_backup, browse_volume, read_volume_file, create_volume_directory, upload_to_volume, delete_volume_file

### Projects / Compose (17)
list_projects, get_project, deploy_project, redeploy_project, remove_project, update_project, get_project_counts, project_down, restart_project, build_project, archive_project, unarchive_project, pull_project_images, get_project_compose, get_project_file, update_project_services, get_project_runtime

### Networks (9)
list_networks, create_network, inspect_network, remove_network, connect_container_to_network, disconnect_container_from_network, prune_networks, get_network_counts, get_network_topology

### Environments (5)
list_environments, get_environment, create_environment, update_environment, remove_environment

### System (9)
get_docker_info, get_docker_version, prune_system, get_system_health, check_system_upgrade, trigger_upgrade, start_all_containers, start_stopped_containers, stop_all_containers

### Activities & Events (7)
list_activities, get_activity, cancel_activity, clear_activity_history, list_events, get_environment_events, delete_event

### Container Registries (6)
list_registries, create_registry, get_registry, update_registry, delete_registry, test_registry

### Vulnerabilities (6)
get_vulnerability_summary_all, list_all_vulnerabilities, ignore_vulnerability, list_ignored_vulnerabilities, unignore_vulnerability, get_scanner_status

### Webhooks (5)
trigger_webhook, list_webhooks, create_webhook, update_webhook, delete_webhook

### Updater (3)
run_updater, get_updater_status, get_updater_history

### Ports (1)
list_ports

## Usage

All resource tools accept `env_id: str = "0"` to target a specific Arcane environment (local Docker is "0", remote agents use UUIDs). Remote agent operations can pass `agent_token: str | None` for authentication via the `X-Arcane-Agent-Token` header.

Destructive operations (remove, prune, kill, restore, etc.) require `confirm: bool = False` — set to `True` to execute.

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
