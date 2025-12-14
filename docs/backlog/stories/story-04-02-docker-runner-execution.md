---
type: story
id: ST-04-02
title: "Docker runner execution (Sibling Containers + Security)"
status: ready
owners: "agents"
created: 2025-12-14
epic: "EPIC-04"
acceptance_criteria:
  - "Given a tool version, when executed, then a new sibling Docker container is spawned using the Docker SDK (not shelling out to the Docker CLI)."
  - "Given the app is running in a container, when the runner starts, it uses Docker API archive copy (put/get archive) or Docker volumes for I/O, never host binds."
  - "Given the runner container is configured, it runs with a read-only root filesystem and only tmpfs/volumes are writable."
  - "Given a script execution, when it completes, then stdout/stderr/html_output are returned to the app for DB storage and artifacts are written to disk."
  - "Given a runner image, when built, it includes a non-root user and curated Python packages."
  - "Given the runner container spawns, then it drops all capabilities, runs as non-root, and uses no-new-privileges."
  - "Given a retention policy (e.g., 7 days), when the cleanup task runs, then old artifact files are deleted."
---

## Context

This story implements the execution infrastructure. It must support **sibling container** execution via `docker.sock`
(Docker-outside-of-Docker) since the main app is containerized. It prioritizes security and cleanliness.

## Scope

- **Protocol boundary (protocol-first DI):**
  - Add protocols for execution + artifact management (e.g. `ToolRunnerProtocol`, `ArtifactManagerProtocol`) so
    application handlers depend on protocols, not Docker SDK implementations.
- **Runner Infrastructure:** `src/skriptoteket/infrastructure/runner/`
  - `docker_runner.py`: Uses `docker` Python SDK.
  - Lifecycle: create container, inject script/input via `put_archive`, start, wait/timeout, fetch logs and
    `/work/output` via `get_archive`, then remove.
- **Security Profile:**
  - Image: `Dockerfile.runner` (new file) -> based on `python:3.13-slim`, create user `runner`.
  - Runtime: `--cap-drop ALL`, `--user runner`, `--security-opt no-new-privileges`, `--pids-limit`, and
    `--network none` (sandbox).
  - Filesystem: `--read-only` root filesystem + tmpfs/volume mounts for `/work` and `/tmp`.
- **Configuration:**
  - Load limits and paths from `Settings` (explicit keys; exact names can vary but MUST be centralized in config):
    - Runner image: `RUNNER_IMAGE`
    - Concurrency: `RUNNER_MAX_CONCURRENCY`
    - Timeouts (seconds): `RUNNER_TIMEOUT_SANDBOX_SECONDS`, `RUNNER_TIMEOUT_PRODUCTION_SECONDS`
    - Resource limits: `RUNNER_CPU_LIMIT`, `RUNNER_MEMORY_LIMIT`, `RUNNER_PIDS_LIMIT`
    - Artifact storage: `ARTIFACTS_ROOT`, `ARTIFACTS_RETENTION_DAYS`
    - Safety caps for DB fields: `RUN_OUTPUT_MAX_STDOUT_BYTES`, `RUN_OUTPUT_MAX_STDERR_BYTES`, `RUN_OUTPUT_MAX_HTML_BYTES`
- **Cleanup:**
  - Background task (or simple cron script) to prune `/var/lib/skriptoteket/artifacts/` > N days.

## Transaction boundary (REQUIRED)

Execution can take seconds to minutes; handlers MUST NOT hold DB transactions open while waiting for the runner:

1. Insert `tool_runs` row with `status=running` and commit.
2. Execute the runner.
3. Update the same `tool_runs` row with final `status`, `stdout`, `stderr`, `html_output`, `error_summary`,
   `artifacts_manifest`, and commit.

## Async integration and backpressure (REQUIRED)

- Docker SDK calls are synchronous and MUST NOT run on the event loop.
- All execution MUST be performed off the event loop (thread pool) and guarded by a global concurrency cap
  (`RUNNER_MAX_CONCURRENCY`).
- When saturated, new runs MUST be rejected (no in-process queueing).

See ADR-0016 for the v0.1 concurrency + backpressure policy.

## Runner output contract (REQUIRED)

Define a stable, versioned contract for how the runner returns results to the app. Recommended:

- See ADR-0015 for the canonical contract and compatibility rules.

- Runner writes a single JSON file at `/work/result.json` with:
  - `status`: `succeeded|failed|timed_out`
  - `html_output`: HTML string (may be empty on failure)
  - `error_summary`: short string for end-user/admin display (no raw tracebacks)
  - `artifacts`: list of `{ "path": "output/...", "bytes": <int> }` (paths are relative to `/work`)
- The app stores:
  - `stdout`/`stderr` captured from container logs (truncated to caps)
  - `html_output` and `error_summary` from `result.json` (truncated to caps)
  - `artifacts_manifest` generated from the extracted `/work/output` directory and the `artifacts` list

### Artifacts manifest rules (REQUIRED)

- Artifact paths must be relative and must not contain `..` segments.
- The app should generate stable `artifact_id` values (e.g., slugified path) and include byte sizes.
- Large/binary artifacts are written to disk under `/var/lib/skriptoteket/artifacts/{run_id}/...` and referenced only
  via `tool_runs.artifacts_manifest` (never stored in Postgres blobs).

## Script Contract

```python
def run_tool(input_path: str, output_dir: str) -> str:
    """
    Standard contract.
    Returns HTML string.
    """
```

## Docker Invocation Strategy

Instead of host bind mounts, the app uses Docker Engine APIs via the Python Docker SDK:

1. Create container (do not auto-remove; cleanup is explicit).
2. Inject script + input file via Docker archive copy (`put_archive`) into `/work`.
3. Start container.
4. Wait for exit (enforce timeout; on timeout, kill container and mark run as `timed_out`).
5. Capture stdout/stderr via container logs.
6. Retrieve `/work/output` via Docker archive copy (`get_archive`), then write artifacts to
   `/var/lib/skriptoteket/artifacts/{run_id}/...` and persist a manifest in the DB.
7. Remove container (and any per-run volumes if used).
