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

- Admin endpoints: create draft, save, submit review, publish
- Web UI: code editor (syntax highlighting), "Run sandbox" button
- Display: HTML preview, logs (stdout/stderr tabs), artifacts list
- Template/stub generation for new scripts

### ST-04-04: Governance, audit, and rollback

- RBAC enforcement: contributor/admin/superuser permissions
- Audit events for all version transitions and executions
- Rollback action (publish derived-from older version)
- Version history view with actor/timestamp

### ST-04-05: User execution of active tools

- Public (authenticated) endpoint for running active tools
- Runner integration for production context (different timeouts; v0.2 keeps network disabled by default)
- Result view for end-users (HTML only, no logs/debug info)
- Metrics and usage tracking

## Risks

- Docker socket access expands blast radius (mitigate: consider dedicated runner service later)
- Heavy scripts may exceed request timeout (mitigate: async execution queue in future epic)
- Runner image dependency management requires rebuild for new packages

## Dependencies

- EPIC-02 (identity and RBAC) - role guards and current user resolution
- EPIC-03 (script governance) - suggestion → draft tool flow feeds into this epic
- ADR-0012, ADR-0013, ADR-0014 (storage, execution, versioning decisions)
