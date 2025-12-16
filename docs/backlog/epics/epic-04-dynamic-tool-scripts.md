---
type: epic
id: EPIC-04
title: "Dynamic tool scripts (admin-authored Python without redeploy)"
status: proposed
owners: "agents"
created: 2025-12-14
outcome: "Admins can implement, test, and publish Python tool scripts via the web UI without repository changes or redeployment."
---

## Scope

This epic enables the full script authoring and execution lifecycle:

- **Versioned script model**: DB schema, domain entities, repositories for tool versions
- **Docker runner execution**: Ephemeral container per run with resource limits
- **Admin editor UI**: Code editor, sandbox execution, logs/artifacts display
- **Governance and audit**: RBAC enforcement, version transitions, rollback capability
- **Invariant alignment with EPIC-03**: “published implies runnable” (see Cross-cutting clarifications)

## Cross-cutting clarifications (recommended)

### Published implies runnable (system invariant)

- A tool is runnable for end-users only when:
  - `tools.is_published == true`
  - `tools.active_version_id != null`
  - `tool_versions.id == tools.active_version_id` and `tool_versions.state == 'active'`
- ST-03-03 already enforces this on *tool publish*; EPIC-04 must uphold it on *version publish/rollback* and *user
  execution*:
  - ST-04-04 MUST update `tools.active_version_id` to point to the newly created ACTIVE version during publish/rollback.
  - ST-04-05 MUST return 404 if the tool is depublished or if the active pointer is missing/invalid/non-ACTIVE (defense
    in depth against drift).

### Long-running runner calls MUST NOT hold DB transactions open

- Handlers that trigger Docker execution (sandbox or production) should not keep a DB transaction open while waiting for
  the container to finish.
- Recommended pattern:
  1. Create `ToolRun(status=running)` and commit.
  2. Execute runner.
  3. Persist results (status/stdout/stderr/html_output/artifacts_manifest) in a second commit.

## Stories

### ST-04-01: Versioned script model

- DB schema + migrations for `tool_versions` and `tool_runs`
- Domain entities in new `scripting` domain
- Repository implementations with version state transitions
- Single active version constraint enforced

### ST-04-02: Docker runner execution

- Runner wrapper (`_runner.py`) for script execution contract
- Per-run workdir management (input/output/artifacts)
- Capture stdout/stderr + HTML output + artifacts manifest
- Timeouts + memory/CPU caps via Docker limits
- Sandbox vs production context isolation

### ST-04-03: Admin script editor UI

- Admin endpoints: create draft, save draft snapshot, submit for review, run sandbox
- Web UI: code editor (syntax highlighting), "Run sandbox" button
- Display: HTML preview, logs (stdout/stderr tabs), artifacts list
- Template/stub generation for new scripts

### ST-04-04: Governance, audit, and rollback

- RBAC enforcement: contributor/admin/superuser permissions
- Audit events for all version transitions and executions
- Version publish + rollback (publish derived-from older version)
- Version history view with actor/timestamp

### ST-04-05: User execution of active tools

- Public (authenticated) endpoint for running active tools
- Runner integration for production context (different timeouts; v0.2 keeps network disabled by default)
- Result view for end-users (HTML only, no logs/debug info)
- Metrics and usage tracking

### ST-04-06: Repo script bank seeding

- Repo-level script bank (svenska, teacher-first) + CLI seeding till DB (idempotent per slug)
- Runbook för körning (lokalt + prod/Docker)

## Risks

- Docker socket access expands blast radius (mitigate: consider dedicated runner service later)
- Heavy scripts may exceed request timeout (mitigate: async execution queue in future epic)
- Runner image dependency management requires rebuild for new packages

## Dependencies

- EPIC-02 (identity and RBAC) - role guards and current user resolution
- EPIC-03 (script governance) - suggestion → draft tool flow feeds into this epic
- ADR-0012, ADR-0013, ADR-0014 (storage, execution, versioning decisions)
