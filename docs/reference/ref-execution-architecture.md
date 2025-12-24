---
type: reference
id: REF-execution-architecture
title: "Script Execution Architecture"
status: active
owners: "agents"
topic: "architecture"
created: 2025-12-17
---

# Script Execution Architecture: Analysis of "Testyta", "Mina verktyg", and "Katalog"

This document maps the plumbing and logic behind script execution ("KÖR" and "TESTKÖR") within the Skriptoteket architecture.

## 1. Execution Context

Script execution is **isolated** within ephemeral Docker containers, managed by the application infrastructure.

*   **Runner Image:** Defined by `RUNNER_IMAGE` (default: `skriptoteket-runner:latest`).
    *   **Base:** `python:3.13-slim` (matches main app).
    *   **Dependencies:** Syncs `prod` dependencies from `pyproject.toml` (e.g., `pdm`, `pandas` if added) + system libraries (`pandoc`, `libcairo2`, `libpango*`) for document generation.
    *   **User:** Runs as non-root user `runner` (uid 10001).
*   **Environment Variables (Host):**
    *   `RUNNER_MAX_CONCURRENCY`: Limits simultaneous runs (default: 1).
    *   `RUNNER_TIMEOUT_SANDBOX_SECONDS`: Timeout for "TESTKÖR" (default: 60s).
    *   `RUNNER_TIMEOUT_PRODUCTION_SECONDS`: Timeout for "KÖR" (default: 120s).
    *   `RUNNER_CPU_LIMIT`, `RUNNER_MEMORY_LIMIT`: Resource constraints.
*   **Environment Variables (Container):**
    *   `SKRIPTOTEKET_ENTRYPOINT`: Function to call (default: `run_tool`).
    *   `SKRIPTOTEKET_SCRIPT_PATH`: Path to script (`/work/script.py`).
    *   `SKRIPTOTEKET_INPUT_DIR`: Directory containing all uploaded files (`/work/input`).
    *   `SKRIPTOTEKET_INPUT_MANIFEST`: JSON listing all input files (`{"files":[{name,path,bytes}]}`).
    *   `SKRIPTOTEKET_MEMORY_PATH`: Path to per-run memory JSON (`/work/memory.json`, contains `{"settings": {...}}`).
    *   `SKRIPTOTEKET_OUTPUT_DIR`: Directory for artifacts (`/work/output`).

## 2. Input/Output Data Flow

Data flows from the web request into the container and back via a standardized contract.

### Input
1.  **Source:**
    *   **KÖR:** User uploads one or more files via `POST /tools/{slug}/run`. Script source is fetched from the *active* version in DB.
    *   **TESTKÖR:** User uploads one or more files via `POST /admin/tool-versions/{version_id}/run-sandbox`. Script source is fetched from the *specific* version (draft or published) in DB.
2.  **Transformation:**
    *   Input files and Script source are packaged into a **tar archive**.
    *   Archive is streamed into the Docker container at `/work`, placing all inputs under `/work/input/`.

### Memory (per-run JSON)

The app injects a `memory.json` file into the runner container and sets `SKRIPTOTEKET_MEMORY_PATH`.

- Path: `/work/memory.json`
- Current shape: `{"settings": {...}}` (per-user, per-tool, schema-versioned settings; may be `{}`).

### Output
1.  **Destinations:**
    *   **Stdout/Stderr:** Captured and truncated (max ~200KB).
    *   **Return Value:** The entrypoint returns either a string (HTML, backwards compatible) or a dict (typed UI contract v2); the runner writes `result.json`.
    *   **Artifacts:** Any file written to `/work/output` is captured.
2.  **Transformation:**
    *   Internal `_runner.py` wrapper catches exceptions and writes a `result.json`.
    *   `result.json` and `/work/output` are tarred and streamed back to the host.
    *   Host parses JSON and stores artifacts in `ARTIFACTS_ROOT`.

## 3. Control Flow & Logic

Both execution types converge on the `ToolRunnerProtocol` but start from different handlers.

### "KÖR" (Production Run)
1.  **Web:** `src/skriptoteket/web/pages/tools.py` -> `execute_tool`
2.  **Command:** `RunActiveToolCommand`
3.  **Handler:** `RunActiveToolHandler`
    *   *Check:* Tool must be published and have an active version.
4.  **Orchestrator:** `ExecuteToolVersionHandler`
    *   *Action:* Creates `ToolRun` (status: RUNNING).
    *   *Action:* Calls `DockerToolRunner.execute` with `production_timeout`.
    *   *Action:* Updates `ToolRun` with result (status: SUCCEEDED/FAILED).

### "TESTKÖR" (Sandbox/Test Area)
1.  **Web:** `src/skriptoteket/web/pages/admin_scripting_runs.py` -> `run_sandbox`
2.  **Command:** `RunSandboxCommand`
3.  **Handler:** `RunSandboxHandler`
    *   *Check:* User must be contributor/maintainer.
4.  **Orchestrator:** `ExecuteToolVersionHandler`
    *   *Action:* Creates `ToolRun` (status: RUNNING).
    *   *Action:* Calls `DockerToolRunner.execute` with **`sandbox_timeout`**.
    *   *Action:* Updates `ToolRun` with result.

## 4. Verification of Assumptions

*   **Docker Availability:** The system *assumes* the host has a Docker daemon reachable via standard socket (`docker.from_env()`).
*   **Image Presence:** Assumes `RUNNER_IMAGE` is built and available locally or pullable.
*   **Script Contract:** Assumes user script defines a function matching `def run_tool(input_dir: str, output_dir: str) -> str`.
*   **File System:** Assumes `ARTIFACTS_ROOT` is writable and persistent.
*   **Network:** The runner container has `network_mode="none"`, assuming scripts **do not** need internet access.

## 5. Tool Integration & Extensibility

*   **Katalog (Catalog):**
    *   Exposes the public interface.
    *   Constrained to *Active* versions only.
*   **Mina verktyg (My Tools):**
    *   Acts as the management portal.
    *   Links to the **Testyta**.
*   **Testyta (Test Area):**
    *   Located at `/admin/tools/{tool_id}`.
    *   Provides the *Draft* context.
    *   Allows testing *any* version (Draft, Active, Archived).

### Extensibility Assessment
*   **High:** The `ToolRunnerProtocol` decouples the web app from the execution engine. Replacing Docker with Kubernetes or AWS Lambda would only require a new adapter in `infrastructure/`.
*   **Medium:** Adding new output types (e.g., JSON structure instead of HTML) requires changing `_runner.py` and the `ToolExecutionResult` model, but the pipe is generic.
*   **Low:** Real-time feedback (streaming logs) is currently not supported; the system waits for the container to exit before processing output.
