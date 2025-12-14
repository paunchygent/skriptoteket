---
type: reference
id: REF-architectural-review-epic-04
title: "EPIC-04 Pre-Implementation Architecture Review"
status: active
owners: "agents"
created: 2025-12-14
topic: "scripting"
---

## Executive Summary

EPIC-04 is in a good state to proceed: ST-04-01 provides a coherent versioned script/run foundation and matches the intended "published implies runnable" invariant. The primary architectural risk sits in ST-04-02: using the Docker SDK from an async FastAPI app (blocking calls + docker.sock blast radius) is acceptable for v0.1 only if we enforce strict sandboxing, concurrency caps, and a clean separation between "control-plane failures" and "execution outcomes."

---

## Foundation Assessment (ST-04-01)

Overall, the domain model and persistence layout are sound and aligned with ADR-0014 (append-only + single ACTIVE) and ADR-0012 (logs in DB, artifacts on disk).

### Strengths

- **Clear lifecycle model**: VersionState and RunStatus/RunContext are explicit, and state transition factories enforce key preconditions (e.g., only DRAFT → IN_REVIEW; only IN_REVIEW → publish).
- **Copy-on-activate**: Implemented in domain (`publish_version()` returns a structured `PublishVersionResult`) which keeps the "published timeline" auditable and rollback-friendly.
- **DB constraints reflect invariants**: Partial unique index for single ACTIVE and `(tool_id, version_number)` uniqueness are correct for ensuring a stable linear history.

### Concerns & Recommendations

1. **Hash semantics**: `content_hash` is computed from `source_code` only. If entrypoint changes, it may represent a materially different runnable artifact but keep the same hash. Consider hashing `{entrypoint}\n{source_code}` or adding a separate hash for "runnable contract identity."

2. **Concurrency on version_number allocation**: `get_next_version_number()` is `max()+1`, which can race under concurrent saves. The unique constraint will prevent corruption, but handlers should explicitly retry once on `IntegrityError` (or lock on the tool row) to avoid spurious failures.

3. **Repository update behavior**: `ToolRunRepository.update()` and `ToolVersionRepository.update()` return the input object if the DB row is missing, which can mask data integrity issues. For use-cases that "must exist" (e.g., finishing a run that was just created), prefer raising `DomainError(NOT_FOUND)` to surface unexpected drift.

4. **Web router rule compliance**: `.agent/rules/040-fastapi-blueprint.md` forbids `from __future__ import annotations` in router modules; `src/skriptoteket/web/router.py` currently includes it and should be corrected when you touch routing for EPIC-04.

---

## ST-04-02: Docker Runner

### Recommended Approach

Proceed with the sibling-container model for v0.1, but implement it behind a narrow protocol boundary and ensure all Docker SDK calls run off the event loop. This keeps the current "single container app" deployment style while leaving a clean seam for a future dedicated runner service (ADR-0013 already frames this path).

### Key Architectural Shape

Add a protocol (either in `protocols/scripting.py` or a new `protocols/runner.py`):

- `ToolRunnerProtocol.run_version(...)` → `RunnerOutcome`
- `ArtifactManagerProtocol` for persistence/retrieval/cleanup

Provide an infrastructure implementation:

- `infrastructure/runner/docker_runner.py` implements `ToolRunnerProtocol`
- `infrastructure/artifact_manager.py` implements `ArtifactManagerProtocol`
- `infrastructure/runner/runner_config.py` holds resource/timeout caps derived from Settings

### Async Correctness (Critical)

- The Docker SDK (`docker` / `docker-py`) is synchronous. Do not call it directly from handlers/routes.
- Wrap runner calls with `asyncio.to_thread(...)` (or `anyio.to_thread.run_sync(...)`) and enforce a global semaphore (e.g., `RUNNER_MAX_CONCURRENCY`) to avoid threadpool/engine exhaustion.

### Transaction Boundary

Follow the epic's required pattern:

1. Write `ToolRun(status=RUNNING)` and commit
2. Execute runner outside the transaction
3. Persist final output in a second transaction

This is explicitly required by EPIC-04 docs and aligns with the existing UoW usage pattern.

### Security Considerations

Given docker.sock access is the highest-risk element, security must be "defense in depth," not just container flags.

#### Runner Container Hardening (Minimum for v0.1)

- `network_mode="none"` (at least for sandbox; and per spec, production also defaults to none until policy exists)
- Non-root user (`--user runner`), `--cap-drop ALL`, `--security-opt no-new-privileges`, `--pids-limit`, read-only root FS
- tmpfs mounts for `/work` and `/tmp` with `noexec,nosuid,nodev`
- Do not mount docker.sock into runner containers (explicit in ADR-0013)

#### docker.sock Blast Radius Mitigations (v0.1 Pragmatic)

- Ensure the app container image is minimal and kept current; minimize installed tools that could be leveraged if compromised
- Limit the runner feature exposure to authenticated roles only (admin/contributor for sandbox; user only through constrained "run published tool" flow)
- Consider running the Docker engine on a dedicated host (even if it's the same machine, isolate via ops practices). This is operational rather than code, but important for v0.1 risk acceptance.

### Configuration Strategy

Extend Settings with explicit runner/artifact limits (as already listed in ST-04-02). Keep the runner-specific derived values in `RunnerConfig` so application handlers do not parse memory/cpu strings.

#### Recommended Settings Additions (Minimum Viable)

**Runner:**

- `RUNNER_IMAGE`
- `RUNNER_TIMEOUT_SANDBOX_SECONDS`, `RUNNER_TIMEOUT_PRODUCTION_SECONDS`
- `RUNNER_CPU_LIMIT`, `RUNNER_MEMORY_LIMIT`, `RUNNER_PIDS_LIMIT`
- `RUNNER_MAX_CONCURRENCY`

**Output caps:**

- `RUN_OUTPUT_MAX_STDOUT_BYTES`, `RUN_OUTPUT_MAX_STDERR_BYTES`, `RUN_OUTPUT_MAX_HTML_BYTES`

**Artifacts:**

- `ARTIFACTS_ROOT`
- Prefer split retention:
  - `ARTIFACTS_RETENTION_SANDBOX_DAYS`, `ARTIFACTS_RETENTION_PRODUCTION_DAYS`
  - Plus a policy toggle like `PRODUCTION_RETAIN_INPUT_FILES: bool = False`

### Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Event-loop blocking / degraded API performance | Run Docker SDK in threads + semaphore + strict timeouts; consider rejecting new runs with a clear admin-visible error if concurrency is saturated |
| Output bloat (stdout/stderr/html) | Enforce truncation at the runner boundary and again at persistence boundary (caps in Settings) |
| Path traversal via artifacts | Artifacts manifest must reject absolute paths and any `..` segments (ST-04-02 explicitly requires this). Normalize and validate on ingestion; never trust runner-supplied paths |
| Runner contract drift | Make `result.json` include `contract_version`; the app validates before parsing |
| Operational risk of docker.sock | Accept for v0.1 with documented guardrails; explicitly plan ADR for "dedicated runner service" in v0.2+ if usage expands |

---

## ST-04-03: Admin Editor

### Handler Organization

Keep handlers under `application/scripting/handlers/` (single domain: scripting). Within that, split by capability to preserve SRP:

```text
handlers/versions/
    create_draft_version.py
    save_draft_version.py
    submit_for_review.py
handlers/runs/
    run_sandbox.py
    get_tool_run.py (can be shared later with ST-04-05)
```

This mirrors the existing catalog pattern (small, single-purpose handlers).

### Cross-Domain Dependency

Version authoring/publishing needs to read tool metadata and eventually update `tools.active_version_id`. Today, `ToolRepositoryProtocol` does not expose a "set active version" method in the provided subset, so plan to add:

```python
ToolRepositoryProtocol.set_active_version_id(
    tool_id: UUID,
    active_version_id: UUID | None,
    now: datetime
) -> Tool
```

This keeps the invariant enforcement in a single place and avoids scripting handlers reaching into SQLAlchemy models.

### API Endpoint Design

Even if the web UI returns HTML, keep the application layer DTOs aligned with `ref-scripting-api-contracts.md` to avoid divergence and to enable a future JSON API with minimal churn.

#### Notable Contract Gaps

RequestChanges endpoints are required by ST-04-04 but are not specified in `ref-scripting-api-contracts.md`. Decide now whether:

- You extend the contract with `POST /admin/tool-versions/{version_id}/request-changes`, or
- You treat it as internal-only for v0.1 and document it as a deliberate omission

#### Sandbox Run Form Handling

- Uploads should be streamed to disk (not read into memory), then selectively retained based on context/policy
- Ensure sandbox run endpoints do not hold the DB transaction open while waiting (required)

### UI/UX Considerations

- Provide a starter template for tools with no versions (explicit in ST-04-03)
- Treat "Save" as append-only: saving creates a new DRAFT version and refreshes the "current head"
- Use HTMX partials for:
  - Run result refresh (`run_result.html`)
  - Version list refresh (`version_list.html`)
  - Artifact list refresh (or as part of run result)
- Make conflict errors actionable: when `expected_parent_version_id` mismatches, return a UI message indicating that the draft head advanced and the user must reload

---

## ST-04-04: Governance

### Authorization Model

Implement explicit scripting-domain policies in `domain/scripting/policies.py`, but keep role guards consistent with existing `require_at_least_role` patterns. The policy should cover:

- Contributor can only edit/view own drafts (ownership via `created_by_user_id`)
- Admin/superuser can operate on all versions
- Publish: admin + superuser
- Rollback: superuser only

#### Practical Approach

- Domain policy functions like `can_view_version(actor, version)` and `can_edit_version(actor, version)` used by handlers
- Continue using `role_guards` for coarse role checks, then apply ownership constraints at the scripting policy layer

### Audit Trail Strategy

The schema already supports audit fields on `tool_versions` and run attribution on `tool_runs`. For v0.1, this is likely sufficient.

If you want stronger audit semantics without adding tables, ensure every state transition handler sets the correct actor/time fields:

- **Submit**: `submitted_for_review_*`
- **Request changes**: `reviewed_*` + new draft derived from reviewed
- **Publish**: `published_*` (on both consumed IN_REVIEW and the new ACTIVE)

### Rollback Safety

Use the same "copy-on-activate" mechanism for rollback (as specified in ST-04-04 / ADR-0014).

Perform publish/rollback in a single transaction:

1. Archive current ACTIVE (if exists) and flush
2. Archive reviewed IN_REVIEW (publish) or leave archived source as-is (rollback source stays archived)
3. Create new ACTIVE and flush
4. Update `tools.active_version_id`
5. Commit

This order avoids violating the partial unique index for ACTIVE.

---

## ST-04-05: User Execution

### Production vs Sandbox Isolation

Use the same runner infrastructure with different config presets:

| Context | Timeout | Resources | Input Retention | Log Visibility |
|---------|---------|-----------|-----------------|----------------|
| Sandbox | Shorter | Lower memory/cpu | Retain for debugging (short retention) | Full logs to admin |
| Production | Longer | Potentially higher | Do not retain by default | Never display to end-users |

I recommend separate handlers:

- `RunSandboxHandler` (admin/contributor constraints; retains debug surfaces)
- `RunActiveToolHandler` (user constraints; enforces "published implies runnable" and hides debug surfaces)

Internally they can share a pure function/service that calls `ToolRunnerProtocol` with `RunContext`.

### Error Handling Strategy

Follow the contracts and the existing `DomainError` usage pattern:

| Condition | Response | Details |
|-----------|----------|---------|
| Not runnable (tool missing, not published, missing/invalid `active_version_id`, or active version is not ACTIVE) | 404 | Defense in depth |
| Execution completes but fails | 200 with `failed`/`timed_out` outcome | Show friendly error view using `ToolRun.error_summary`; do not show stdout/stderr to users |
| Control-plane errors (docker daemon unreachable, unexpected infra error) | 500/502 | Raise `DomainError(INTERNAL_ERROR)` and render a generic error page |

### User Experience

- Keep user flow minimal: upload → run → HTML result, with a clear "Run again" action
- Provide `/my-runs/{run_id}` with ownership checks (404 if not owned)
- If retention may delete artifacts/results, be explicit in UI (e.g., "Results retained for 30 days")

---

## Cross-Cutting Concerns

### Logging & Observability

- Log runner lifecycle events with `correlation_id`: start container, wait outcome, fetch logs, fetch artifacts, cleanup, and any exceptions
- Capture metrics (even if only logs initially): execution duration, success/fail/timeout rates, artifact sizes, truncation counts

### Testing Strategy

| Type | Scope | Notes |
|------|-------|-------|
| Unit tests | Domain transition functions (`save_draft_snapshot`, `submit_for_review`, `publish_version`, `finish_tool_run`) | Pure functions; exhaustively test |
| Contract tests | `_runner.py` output (`result.json`, artifact enumeration rules, `error_summary` sanitization) | Essential: this is the boundary between app and runner |
| Integration tests | Run a small script through Docker in CI | Optional but valuable; if not available, mock `ToolRunnerProtocol` for application tests and run a manual "smoke" suite in staging |

### Performance

- Enforce concurrency caps for runner executions
- Stream file uploads to disk; do not keep full files in memory
- Truncate logs and HTML at safe limits before writing to Postgres

---

## Implementation Sequencing

### Recommended Order

```text
1. ST-04-02 (critical path)
   ├── Define runner contract
   ├── Implement _runner.py and Dockerfile.runner
   ├── Implement ArtifactManager + manifest rules + cleanup script/task
   ├── Implement DockerRunner (thread-wrapped) + output/log caps + timeouts
   └── Wire into DI (di.py) and config (config.py)

2. Parallel after ST-04-02 is stable
   ├── ST-04-03 (admin UI + handlers)
   └── ST-04-05 (user execution + views)
       └── Both depend on same ToolRunnerProtocol and ArtifactManagerProtocol abstractions

3. ST-04-04
   └── Add governance handlers and policies once editor flows exist
       └── Enables end-to-end publishing/rollback UX validation
```

### Estimated Complexity

| Story | Complexity | Key Challenges |
|-------|------------|----------------|
| ST-04-02 | High | Security + async integration + file handling |
| ST-04-03 | Medium | Handler organization + UI state management |
| ST-04-04 | Medium | Careful transactional ordering |
| ST-04-05 | Medium-low | Mostly orchestration + templates |

---

## Open Questions

1. **docker.sock risk acceptance**: Are you comfortable with v0.1 deployment requirements (docker.sock mount) in your target environment, or do you need an earlier move to a dedicated runner host/service?

2. **Runner dependency set**: Who owns updating the runner image and which libraries are "blessed" for v0.1? Without this, admins may expect packages that aren't present.

3. **Retention policy and data sensitivity**: Confirm concrete defaults:
   - Sandbox retention (short)
   - Production retention for outputs/artifacts
   - Production input retention (default off)

4. **Contract gap for Request Changes**: Decide whether to update `ref-scripting-api-contracts.md` now to avoid "implementation vs spec" divergence.

5. **Version-number race strategy**: Decide whether to implement retries or locking; relying only on the unique constraint will produce intermittent admin errors under concurrent saves.

---

## ADR Recommendations

I recommend formalizing two additional ADRs (or advancing the "proposed" ADRs to "accepted" once agreed):

### Required

1. **ADR: Runner Contract & Compatibility**
   - Define `result.json` schema, `contract_version`, truncation rules, and `error_summary` sanitization guarantees

2. **ADR: Execution Concurrency & Backpressure**
   - Define max concurrent runs, queue/reject behavior, and operational limits (CPU/memory per context)
   - Prevents ad-hoc limits scattered across handlers

### Optional (Advisable)

3. **ADR: Artifact Retention & Data Handling**
   - Specify sandbox vs production retention
   - Input retention policy
   - Whether artifacts are considered sensitive by default
