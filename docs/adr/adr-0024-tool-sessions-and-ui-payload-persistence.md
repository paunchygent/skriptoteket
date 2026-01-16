---
type: adr
id: ADR-0024
title: "Tool sessions and UI payload persistence"
status: accepted
owners: "agents"
deciders: ["user-lead"]
created: 2025-12-19
updated: 2026-01-16
links: ["ADR-0022", "ADR-0023", "ADR-0027", "PRD-script-hub-v0.2", "EPIC-10", "EPIC-14"]
---

## Context

Tool UI contract v2 (ADR-0022) introduces:

- `outputs[]` and `next_actions[]` that must be stored for replay/auditing
- `state` that must persist across sessions to enable multi-turn tools

We need a persistence model that:

- supports end users running tools interactively (multi-turn)
- supports both runner-based tools and curated apps (ADR-0023)
- remains safe (strict size budgets)
- is concurrency-safe (multi-tab, double-submit)

## Decision

### 1) Introduce `tool_sessions`

Add a `tool_sessions` table keyed by (`tool_id`, `user_id`, `context`) containing:

- `state` JSONB (size-capped)
- `state_rev` integer used for optimistic concurrency
- `created_at` / `updated_at`

DB sketch (columns, not final):

```sql
tool_sessions (
  id uuid primary key,
  tool_id uuid not null,
  user_id uuid not null,
  context text not null,
  state jsonb not null default '{}'::jsonb,
  state_rev integer not null default 0,
  created_at timestamptz not null,
  updated_at timestamptz not null,
  unique (tool_id, user_id, context)
)
```

Notes:

- `context` enables separate session state for the same tool in different UX flows (e.g. `"default"` vs `"testyta"`).
- The application is the enforcement point for state size caps; DB does not attempt to enforce JSON size.

### 2) Store normalized UI payload per run

Extend `tool_runs` with a stored, normalized `ui_payload` JSONB.

- `ui_payload` is produced by a deterministic normalizer (policy-driven allowlists + size budgets).
- The normalizer is the only code allowed to write `ui_payload` (no raw runner payload persistence).

`ui_payload` is the **rendering source of truth** (SSR and SPA use it), and should be sufficient for:

- replaying what the user saw (outputs + actions + system notices)
- auditing runs (what was rendered and why)
- deterministic rendering (same payload → same UI)

### 3) Support multiple run “source kinds”

Extend `tool_runs` to represent either:

- tool-version runs: `source_kind="tool_version"` with `tool_id` + `version_id`
- curated app runs: `source_kind="curated_app"` with `tool_id` (catalog entry) + `curated_app_id` +
  `curated_app_version`

Notes:

- Curated apps still appear in Katalog as a catalog entry, so they get a `tool_id` (see ADR-0023).
- `curated_app_id` is the stable identifier; `tool_id` may be a deterministic UUID derived from it.

### 4) Minimal API surface

Provide a minimal API for interactive “turn taking”:

- `start_action`: create run, execute, persist `ui_payload`, persist updated state (state_rev)
- `get_session_state`: return current state + available actions
- `get_run`: return stored `ui_payload` + logs/artifacts metadata
- `list_artifacts`: return stored artifacts for a run

### 5) State persistence semantics (initial run + actions)

For multi-step tools, **the platform MUST persist normalized session state after the initial run** so that the first
action run receives the correct server-owned state.

- If a run returns `ui_payload.next_actions[]` (i.e., the tool is interactive), the backend persists the run’s
  `normalized_state` to `tool_sessions` under (`tool_id`, `user_id`, `context`).
- This applies to both:
  - the **initial run** started from the main tool execution endpoint (e.g. upload → run), and
  - subsequent **action runs** started via `start_action` (which uses `expected_state_rev`).
- Rationale: `start_action` MUST supply the current server-owned state to the action run (see action payload transport
  below). If the initial run does not update `tool_sessions`, the first action run will receive stale/empty state and
  workflows that rely on state handoff between steps will fail (e.g. preview → convert flows).

### 6) Action payload transport: `SKRIPTOTEKET_ACTION`

Action runs need both:

- client-provided `action_id` + `input`, and
- server-owned session `state` (from `tool_sessions`, guarded by `expected_state_rev`).

To keep the tool mental model clean and avoid confusing synthetic files in `/work/input/`, action runs MUST provide the
action payload via an explicit environment variable:

```bash
SKRIPTOTEKET_ACTION={"action_id":"...","input":{...},"state":{...}}
```

Notes:

- This applies to both production action runs and editor sandbox action runs.
- Uploaded/session files remain in `/work/input/` and are listed in `SKRIPTOTEKET_INPUT_MANIFEST`; the action payload is
  not a file.
- Tool authors SHOULD prefer helper functions from the runner toolkit (ST-14-19) rather than hand-parsing env vars.

## API shape (minimal, sketch)

These endpoints are intentionally small so they can back the full SPA (ADR-0027) and any remaining legacy UI during migration.

### 1) `start_action`

Starts a turn, executes, persists run + state. Requires optimistic concurrency.

Request (example):

```json
{
  "tool_id": "uuid",
  "context": "default",
  "action_id": "confirm_flags",
  "input": { "notify_guardians": true },
  "expected_state_rev": 3
}
```

Response (example):

```json
{
  "run_id": "uuid",
  "state_rev": 4
}
```

### 2) `get_session_state`

Returns the current session state for a tool in a context.

Response (example):

```json
{
  "tool_id": "uuid",
  "context": "default",
  "state": {},
  "state_rev": 4,
  "latest_run_id": "uuid"
}
```

### 3) `get_run`

Returns the stored normalized `ui_payload` for replay/rendering.

Response (example):

```json
{
  "run_id": "uuid",
  "status": "succeeded",
  "ui_payload": { "contract_version": 2, "outputs": [], "next_actions": [] },
  "artifacts": [{ "path": "output/report.pdf", "bytes": 120000 }]
}
```

### 4) `list_artifacts`

Returns artifacts metadata + download URLs (the download route itself may reuse existing infrastructure).

Response (example):

```json
{
  "run_id": "uuid",
  "artifacts": [
    { "path": "output/report.pdf", "bytes": 120000, "download_url": "/api/runs/uuid/artifacts/report.pdf" }
  ]
}
```

## UI policy profiles (default vs curated)

Normalization is policy-driven to support:

- strict safety/UX constraints for user-authored tools (default)
- a curated owner-authored path with higher budgets and additional UI capabilities (curated)

The policy profile is selected per tool/run (see `UiPolicyProviderProtocol` below).

### Default policy (user-authored tools)

Intended for contributor/admin-authored scripts executed in the runner.

- Output kinds: `notice`, `markdown`, `table`, `json`, `html_sandboxed`, `vega_lite` (restricted; see below)
- No arbitrary JS; `html_sandboxed` is always iframe-sandboxed without scripts.
- Budgets + caps (initial):
  - max `state`: 64 KiB
  - max `ui_payload`: 768 KiB
  - max outputs: 50
  - max next_actions: 10
  - action fields: max 25 fields/action
  - markdown: max 64 KiB
  - html_sandboxed: max 96 KiB
  - json output: max 96 KiB; max depth 10; max keys 1000; max array length 2000
  - table: max 750 rows; max 40 columns; max 512 bytes/cell
  - vega_lite: max 512 KiB/spec (restrictions required below)
  - enum: max 100 options; multi_enum: max 200 options

### Curated policy (owner-authored curated apps)

Intended for curated apps shipped from the repo and not editable via the tool editor workflow.

- Output kinds: default allowlist (including `vega_lite`)
- Budgets + caps (initial):
  - max `state`: 256 KiB
  - max `ui_payload`: 1024 KiB
  - max outputs: 150
  - max next_actions: 25
  - action fields: max 60 fields/action
  - markdown: max 256 KiB
  - html_sandboxed: max 192 KiB
  - json output: max 256 KiB; max depth 20; max keys 5000; max array length 10000
  - table: max 2500 rows; max 80 columns; max 1024 bytes/cell
  - vega_lite: max 512 KiB/spec (restrictions required below)
  - enum: max 300 options; multi_enum: max 600 options

Curated policy is not “unlimited”; it remains capped to protect DB size and UX stability.

## Validation rules (initial allowlists + caps)

The application validates and normalizes all UI-relevant payloads before storage:

- Allowed output kinds and action field kinds are enforced by policy profile.
- Unknown kinds are dropped and replaced with a system notice output.
- All strings are size-capped; output lists are count-capped.
- Nested JSON (`state`, `json` output) is depth-capped and key-count-capped.

### Vega-Lite restrictions (when enabled)

If `vega_lite` is enabled by policy, the platform must apply strict restrictions:

- Inline-only data:
  - allow `data.values`
  - disallow any `data.url`
- Data caps:
  - `data.values`: max 4000 rows
- Spec caps:
  - max 512 KiB/spec (canonical JSON bytes)
- Composition caps:
  - max depth: 8 (nested specs via `layer`/`concat`/`hconcat`/`vconcat`/`facet`/`repeat`)
  - max layers: 16
- External resources:
  - disallow `mark: "image"` / `{"type":"image"}` (image URLs)

If a spec violates restrictions, the platform drops the `vega_lite` output deterministically and adds a system notice
explaining what was blocked and why.

## Deterministic UI payload normalizer (sketch)

Normalization must be deterministic and unit-testable. Inputs to normalization:

1. Raw execution result (runner contract v2 or curated app contract v2)
2. Backend-injected actions/capabilities (policy-gated)
3. The selected UI policy profile (budgets + allowlists)

High-level algorithm:

1. Validate contract version, status, and basic field types.
2. Normalize `state` (ensure JSON object; cap size/depth; record truncation as a notice).
3. Normalize `outputs[]`:
   - validate kind is allowlisted by policy
   - apply kind-specific caps (e.g. table rows/cols, markdown length)
   - replace invalid outputs with `notice` outputs (do not store raw invalid data)
4. Merge `next_actions[]` with backend-injected actions:
   - action IDs must be unique; conflicts are treated as contract violations
   - ordering is deterministic (e.g. sort by `action_id` within source buckets)
5. Produce a canonical `ui_payload` that SSR and SPA can render byte-for-byte consistently.

## Protocol seams (protocol-first DI)

To keep the design protocol-first and unit-testable, introduce these seams:

- `UiPolicyProviderProtocol`:
  - decides which policy profile (default/curated) applies to a tool/run and exposes budgets/allowlists
- `BackendActionProviderProtocol`:
  - returns backend-injected actions/capabilities allowed for the subject + user + policy
- `UiPayloadNormalizerProtocol`:
  - takes raw contract v2 + backend-injected actions + budgets and returns the stored `ui_payload`

Implementations live in infrastructure; application handlers depend on protocols only.

## Consequences

### Benefits

- Enables multi-turn tools with explicit, auditable state changes.
- Keeps UI output safe: only normalized payload is stored/rendered.
- Supports curated apps without forcing them into the tool version workflow.

### Tradeoffs / Risks

- Adds DB schema changes (new table + new columns) and migration complexity.
- Requires careful size budgeting to avoid DB bloat (state/payload caps are mandatory).
- Requires clear ownership for where actions come from (runner vs backend vs curated).
- `vega_lite` is enabled by policy; the restrictions described above MUST be implemented before the platform accepts and
  renders vega_lite outputs (security/performance risk).
