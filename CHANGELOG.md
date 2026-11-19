# Changelog

Entries start at 0.4.0. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versions follow [SemVer](https://semver.org/).

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
