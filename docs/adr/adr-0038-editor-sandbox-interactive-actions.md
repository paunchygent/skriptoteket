---
type: adr
id: ADR-0038
title: "Editor sandbox interactive actions (next_actions + server-owned state)"
status: accepted
owners: "agents"
deciders: ["user-lead"]
created: 2025-12-25
updated: 2025-12-28
links: ["ADR-0022", "ADR-0024", "ADR-0027", "ADR-0030", "EPIC-14"]
---

## Context

The Tool UI contract v2 (ADR-0022) supports multi-step tools via:

- `ui_payload.next_actions[]` (platform-rendered action forms)
- persisted session `state` with optimistic concurrency (`state_rev`) (ADR-0024)

In the **tool editor sandbox** (`SandboxRunner.vue`), runs currently render outputs/artifacts but **ignore**
`next_actions`, making it impossible to test multi-step workflows during authoring.

Additionally, sandbox interactivity must respect the same safety and correctness boundaries as production:

- **State is server-owned** (tools must not trust client-provided state).
- **Concurrency is explicit** using `expected_state_rev` (multi-tab / double-submit safe).
- Action runs should behave like production: action submission provides `action_id + input`, and the platform supplies
  the current server-side state.

## Decision

### 1) Sandbox uses `tool_sessions` with a sandbox-specific context

We will persist normalized tool state for sandbox runs using the existing `tool_sessions` model (ADR-0024).

- Key: (`tool_id`, `user_id`, `context`)
- Context: `sandbox:{version_id}` (UUID is short enough to satisfy the 64-char context cap)

This ensures sandbox interactivity:

- does not collide with production `"default"` sessions
- remains concurrency-safe (`state_rev`)
- stays aligned with the runtime architecture

**Pre-snapshot note:** The current implementation uses `sandbox:{version_id}`. Once snapshot preview
(ST-14-06 / ADR-0044) is implemented, sandbox sessions and actions will move to
`sandbox:{snapshot_id}` and the session endpoint will accept an optional `snapshot_id`
to select the snapshot-scoped context.

### 2) Editor API supports sandbox session + action submission

Add editor-scoped endpoints under `/api/v1/editor`:

- Run sandbox (existing): executes a specific `tool_version` in `RunContext.SANDBOX` and **updates the sandbox session
  state** (`tool_sessions`) from the normalized state result.
- Nice-to-have: include `state_rev` in the run-sandbox response so the UI can enable action submission without an extra
  session fetch roundtrip.
- Get sandbox session state: returns `state_rev` (and optionally `state` for debugging) for the sandbox context.
- Start sandbox action: accepts `{action_id, input, expected_state_rev}` and:
  - reads current state from the sandbox session
  - executes the same `tool_version` with `action.json`
  - updates the sandbox session to the new normalized state
  - returns `{run_id, state_rev}`

The editor API MUST NOT accept client-provided `state`.

### 3) Frontend renders `next_actions` and uses `state_rev` gating

`SandboxRunner.vue` will render action forms using the existing `ToolRunActions` component (parity with `ToolRunView`).

Action submission is disabled until the editor UI has a `state_rev` for the sandbox session, and conflicts are surfaced
as actionable error messaging (409 → “session changed; refresh / retry”).

## Consequences

### Benefits

- Sandbox supports end-to-end testing of multi-step tools during authoring.
- Sandbox behavior matches production semantics (same mental model for tool authors).
- Preserves security boundary: server-owned state + explicit concurrency.

### Tradeoffs / Risks

- Adds persisted state writes for sandbox runs (must use a sandbox-specific context to avoid collisions).
- Tools that need prior input files across steps rely on session-scoped file persistence (ADR-0039). Sandbox action runs
  receive the original uploaded files in `/work/input/` alongside `action.json` (same as production).
