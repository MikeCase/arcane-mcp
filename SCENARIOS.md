# opencode-arcane-mcp — Usage Scenarios

40 tools across 8 categories let you manage Docker entirely through OpenCode. Here are practical scenarios.

---

## 1. Morning Health Check — "Is everything running?"

```text
List all environments
For each env, list all containers
Check for unhealthy containers
```

**Tools used:** `list_environments` → `list_containers` → `inspect_container`

**Real output:**

```
4 environments online
Local Docker:    12 containers, all running
popos:            4 containers, all running
remoteVPS:       10 containers, all running
docker-server-2: 14 containers, 1 unhealthy (personal-website-frontend)
```

No SSHing into boxes. One query.

---

## 2. Rescue a Down Host — "My server crashed, redeploy everything"

**Scenario:** A server went down and came back. All containers are stopped.

```text
list_environments              → find the env ID
list_containers(env_id=...)    → see what's stopped
list_projects(env_id=...)      → check compose projects
redeploy_project(project_id=...) → redeploy each one
```

**Tools used:** `list_containers` → `list_projects` → `redeploy_project` → `start_container`

No `docker-compose up -d` needed. OpenCode handles it.

---

## 3. Clean Up Disk Space — "Docker is eating my disk"

```text
list_images(env_id=...)        → find old/unused images
list_volumes(env_id=...)       → find orphaned volumes
remove_image(image_id, confirm=True)   → clean images
remove_volume(name, confirm=True)      → clean volumes
prune_system(volumes=True, confirm=True) → nuke everything unused
```

**Tools used:** `list_images` → `list_volumes` → `remove_image` → `remove_volume` → `prune_system`

---

## 4. Onboard a New Server — "Add a remote Docker host"

**Scenario:** You spun up a new VPS and installed the Arcane agent.

```text
create_environment(
    name="new-vps",
    api_url="http://10.0.0.5:3553",
    agent_token="arc_..."
)
```

Then instantly:

```text
list_containers(env_id="<new-uuid>")
```

**Tools used:** `create_environment` → `list_environments` → `list_containers`

---

## 5. Update a Stack — "New version of Forgejo is out"

**Scenario:** You noticed `updateInfo.hasUpdate` on a project.

```text
get_project(project_id="...", env_id="...")
→ sees hasUpdate: true

redeploy_project(project_id="...", env_id="...")
→ pulls new image, recreates container
```

**Tools used:** `get_project` → `redeploy_project`

The updateInfo in `list_containers` and `list_projects` shows exactly what needs updating, across all environments.

---

## 6. Debug a Failing Container — "Why is this broken?"

**Scenario:** A container shows "unhealthy" or keeps restarting.

```text
get_container_logs(container_id="...", tail=200)
→ see recent errors

get_container_stats(container_id="...")
→ check CPU/memory pressure

exec_in_container(container_id="...", command="curl localhost:8080/health")
→ run diagnostics inside
```

**Tools used:** `get_container_logs` → `get_container_stats` → `exec_in_container`

---

## 7. Rename or Relocate a Remote Agent — "Server moved to a new IP"

```text
update_environment(
    env_id="<uuid>",
    api_url="http://new-ip:3553"
)
```

Or rotate the token:

```text
update_environment(
    env_id="<uuid>",
    agent_token="arc_new_token_..."
)
```

**Tools used:** `update_environment`

---

## 8. Compose Project Lifecycle — Deploy → Monitor → Remove

```text
deploy_project(
    compose_content="...",
    project_name="my-app",
    env_id="0"
)

# Later...
list_projects(env_id="0")
get_project(project_id="...")

# Update config
update_project(project_id="...", compose_content="...")

# Tear down
remove_project(project_id="...", confirm=True)
```

**Tools used:** `deploy_project` → `list_projects` → `get_project` → `update_project` → `remove_project`

---

## 9. Multi-Environment Audit — "Show me everything, everywhere"

```text
list_environments
→ 4 environments

For each env:
  list_containers(all=True)
  list_images
  list_volumes
  list_networks
  list_projects
```

Aggregate the results to see your entire infrastructure from one conversation. No context switching between servers.

---

## 10. Webhook-Triggered CI — "Update a container from GitHub Actions"

**Scenario:** Your CI pipeline builds a new image, then tells Arcane to update.

```text
trigger_webhook(
    token="arc_wh_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    action="container_update"
)
```

**Tools used:** `trigger_webhook`

No API key needed — webhooks use their own URL-based tokens.

---

## Summary

| Category | What you can do |
|----------|----------------|
| **Containers** | List, inspect, start, stop, restart, remove, create, exec, logs, stats |
| **Images** | List, pull, remove, inspect, tag |
| **Volumes** | List, create, inspect, remove |
| **Networks** | List, create, inspect, remove, connect, disconnect |
| **Projects** | List, get, deploy, redeploy, update, remove compose stacks |
| **Environments** | List, get, create, update, remove remote Docker hosts |
| **System** | Docker info, version, prune |
| **Webhooks** | Trigger inbound webhooks |
