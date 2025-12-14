---
type: adr
id: ADR-0015
title: "Runner result contract and compatibility (result.json + artifacts rules)"
status: accepted
owners: "agents"
deciders: ["user-lead"]
created: 2025-12-14
updated: 2025-12-14
---

## Context

EPIC-04 executes admin-authored scripts in an ephemeral runner container (ADR-0013). The web app persists run state and
renders results, but the runner is the component that actually invokes user code.

To keep this boundary testable, secure, and evolvable, we need a stable, versioned **runner → app** contract for:

- Run outcome (`succeeded|failed|timed_out`)
- User-visible HTML output (if any)
- Safe, user-displayable error summary (no tracebacks)
- Artifacts enumeration and path safety constraints

## Decision

### 1 `result.json` is the runner-to-app contract

The runner writes a UTF-8 JSON file at:

- `/work/result.json`

Schema (contract version `1`):

```json
{
  "contract_version": 1,
  "status": "succeeded|failed|timed_out",
  "html_output": "<p>...</p>",
  "error_summary": "short, safe message or null",
  "artifacts": [
    { "path": "output/report.pdf", "bytes": 120000 }
  ]
}
```

Notes:

- `html_output` may be an empty string on failure. The app applies its own persistence caps.
- `error_summary` MUST be safe for end-user display (no stack traces, no host paths, no secrets).
- `artifacts` is advisory metadata. The source of truth for stored files is the extracted `/work/output/` directory
  validated by the app.

### 2 Compatibility rules

- The app MUST validate `contract_version` before parsing.
- Unknown `contract_version` MUST be treated as a runner contract violation.
- Missing/invalid `result.json` MUST be treated as a terminal execution outcome (`failed`) with a generic
  `error_summary` (and logged as an internal error with correlation_id).

### 3 Artifact path safety rules

Runner-provided artifact paths MUST satisfy all of the following:

- Relative path (no leading `/` or drive prefix).
- No `..` segments after normalization.
- Must be under `output/` (paths outside `output/` are rejected).

The app MUST re-validate these rules on ingestion and MUST NOT trust runner-supplied paths.

### 4 Truncation rules

To prevent DB bloat and UI issues:

- The app is the final enforcement point for truncation caps (Settings-driven) for `stdout`, `stderr`, `html_output`,
  and `error_summary`.
- The runner MAY also truncate `html_output` and `error_summary` defensively, but this does not replace app-side caps.

## Consequences

- Enables contract tests that validate `result.json` schema and safety rules without running the full web stack.
- Provides a clean seam to move execution to a dedicated runner service/host later without rewriting application
  handlers.
- Makes runner failures observable and user-safe: end-users receive only `error_summary`, while admins can still access
  logs stored in `tool_runs` (subject to retention and truncation caps).
