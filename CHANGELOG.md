# Changelog

Entries start at 0.4.0. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versions follow [SemVer](https://semver.org/).

## [1.0.0] — 2026-11-19

Targets **Arcane v3** only. Everything below was verified against a live v3.1.1 instance and its
`/api/openapi.json`, not inferred from the release notes.

### Breaking

- **Arcane v2 support is gone.** The v2 routes (`/api/environments/...`) were dropped by upstream in
  3.0.0. If you are still on Arcane 2.x, pin `arcane-mcp==0.4.0` — the last release that speaks v2.
- **Routes moved to `/api/agents/{id}`**, and resource *actions* moved off their sub-paths onto query
  parameters. `POST /containers/{id}/start` is now `POST /containers/{id}?action=start`; project
  down/restart/archive/unarchive/update-services are `POST /projects/{id}?action=...`; project
  up/redeploy/pull is `POST /projects/{id}/deploy?action=...` with a `ProjectDeployOptions` body.
- **Lists paginate internally.** v3 returns 20 items per page; every list tool now walks
  `pagination.hasNextPage` and returns the whole collection in one envelope. `list_projects`
  previously returned 20 of 34 with no way to ask for the rest.
- **Registries are global**, at `/api/registries` (was `/api/container-registries`). Their request
  body changed: `name` → `description`, `password` → `token`, and updates are `PATCH`.
- **`ignore_vulnerability` signature changed**: `(urn)` → `(image_id, vulnerability_id, pkg_name,
  reason="")`. v3 ignores by image + vulnerability + package, and a Trivy URN has no counterpart.
- **`create_webhook` signature changed**: `(name, url)` → `(name, target_type, action_type,
  target_id="")`. v3 webhooks are internal-event targets, not outbound URLs.
- `kill_container` gained an optional `signal`; `stop_container`/`restart_container` keep their
  `timeout` argument but v3 has no timeout parameter, so it is ignored.

### Fixed

- `PUT /system/health` → **HEAD** `/system/health`; `get_system_health` now reports from the status
  code and headers (GET returns 404 in v3).
- `/image-updates/*` → `/images/updates/*`; `check_image_update` takes `imageRef`.
- `/activities/{id}/cancel` → `POST /activities/{id}?action=cancel`.
- Per-agent events: `/api/events/environment/{id}` → `/api/events/agent/{id}`.
- `/vulnerabilities/ignore` → `/vulnerabilities/ignored`, `scanner-status` → `scanner`.
- System bulk actions: `POST /system/containers?action=startall|startstopped|stopall`.
- Upgrade: `POST /system/upgrade/jobs` (JSON, 202) instead of the old streaming endpoint.
- Volume backups: restore is `POST /volumes/{name}/backups/{id}?action=restore`; `force` moved to a
  query parameter. `browse_volume` / `read_volume_file` now use the v3 **workspace** API.
- Project teardown is a plain `DELETE /projects/{id}`; project update is `PATCH`.
- Container auto-update: `/auto-update` → `/autoupdate`.
- **HTTP timeouts**: httpx's 5-second default is replaced with connect 10 s / read 120 s, overridable
  via `ARCANE_HTTP_TIMEOUT`. A remote Arcane or a quiet `docker pull` used to raise `ReadTimeout`
  after the operation had already started.

### Removed (reported as explicit notices, no HTTP request)

These have no v3 equivalent that can be implemented without the workspace-manifest format:
`exec_in_container`, `get_container_logs`, `get_container_stats` (v3 exposes only
`/containers/{id}/logs/download`, a file), `create_volume_directory`, `upload_to_volume`,
`delete_volume_file`, and `trigger_webhook` (v3 has no trigger endpoint).

## [0.4.0] — 2026-11-19

### Fixed

- **Project creation sent the wrong request entirely.** `POST /api/environments/{env_id}/projects`
  has required `multipart/form-data` since Arcane v2.8.0, with two mandatory text parts: `project`
  (a JSON string whose `composeContent` key carries the compose text) and `manifest`
  (`{"fileChanges": []}` for a plain create). Confirmation tokens now record an `encoding` so
  `confirm_operation` replays JSON or multipart correctly; tokens created before this release
  still replay as JSON.
- **Project update sent `compose` instead of `composeContent`,** so the API rejected or ignored the
  compose body.
- **Project teardown called an endpoint that does not exist.** `DELETE /projects/{id}` 404s on v2,
  which exposes `/projects/{id}/destroy`; v3 moved destroy onto the bare DELETE. Both are handled.
- **Five destructive tools handed out an `operation_hash` computed from a different target string
  than the token stored,** so their own confirmation token could never be validated:
  `remove_network`, `remove_volume`, `restore_volume_backup`, `delete_volume_backup`,
  `delete_volume_file`.

### Added

- **Runtime detection of the Arcane major version.** Arcane v3.0.0 renamed `/api/environments` to
  `/api/agents` (upstream PR #4731) and switched project update from `PUT` to `PATCH`; every route
  is now built through one resolver instead of hardcoded strings, so a single build works against
  both majors. Detection reads `GET /api/version` once per process and falls back to v2 without
  caching if the probe fails. `ARCANE_API_VERSION` overrides detection (`"2"`, `"3"`, `"v3.1.0"`).

### Changed

- Test suite moved to the proposal/confirm flow with request-body assertions, and gained coverage
  for version detection and encoding replay. 98 tests pass; the suite was 14 failed / 11 errors at
  this commit's parent.

### Known issues

- Volume and project file browsing still target the pre-v2.8.0 `/browse` endpoints, which were
  replaced by the `workspace` API. `browse_volume`, `read_volume_file`, `create_volume_directory`,
  `upload_to_volume`, `delete_volume_file` and `get_project_file` return 404 on current Arcane
  releases. Fixing them needs the workspace upload manifest, which is the same machinery as project
  create, so it is tracked separately rather than patched here.

### Acknowledgements

- **[@obstschale](https://github.com/obstschale)** — issue #2. The report correctly traced the
  failure to a transport-level content-type rejection and proposed carrying the encoding on the
  token, which is what this release does. The `422 cannot read multipart form` detail is what made
  the root cause findable.
- **[@czer323](https://github.com/czer323)** — issue #1. The rename was only half the story (the
  create endpoint had no top-level compose key to rename, because the whole request shape had
  changed), but the report pointed at the right functions and got the trail started.
