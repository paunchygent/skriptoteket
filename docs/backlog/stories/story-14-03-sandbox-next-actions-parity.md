---
type: story
id: ST-14-03
title: "Editor sandbox next_actions parity (multi-step testing)"
status: ready
owners: "agents"
created: 2025-12-25
epic: "EPIC-14"
acceptance_criteria:
  - "Given a contributor/admin runs a draft tool in the editor sandbox, when the run returns ui_payload.next_actions, then SandboxRunner renders action buttons and fields using the standard ToolRunActions UI."
  - "Given a sandbox run has next_actions, when the user submits an action, then the backend executes the same tool version in sandbox context using server-owned session state and returns a new run_id."
  - "Given a multi-step tool returns state, when an action completes, then the normalized state is persisted to tool_sessions under a sandbox-specific context and the next action uses that server-side state."
  - "Given the user submits an action with a stale expected_state_rev, when the request is processed, then the API returns 409 and the UI shows an actionable conflict message."
  - "Given the html_to_pdf_preview demo tool is run in the editor sandbox with a small HTML input, when the user clicks 'Konvertera till PDF', then the next step completes and shows results (outputs + artifacts) and the user can 'Börja om'."
dependencies: ["ADR-0022", "ADR-0024", "ADR-0030", "ADR-0038", "ADR-0039", "ST-12-05"]
ui_impact: "Yes (SandboxRunner.vue renders next_actions + action submission UX)"
data_impact: "Yes (tool_sessions writes for sandbox context; no schema change)"
---

## Context

The editor sandbox is the primary authoring/test surface for draft tools, but it currently cannot run multi-step
workflows because it ignores `ui_payload.next_actions`.

This blocks:

- validating interactive tools before publishing
- demos like `html_to_pdf_preview.py` that require a “preview → next action” step

We must implement sandbox interactivity using the same invariants as production:

- server-owned state via `tool_sessions` + `state_rev` (ADR-0024)
- no client-provided state

## Implementation plan (v2)

### Backend (editor sandbox interactivity)

1) Persist sandbox state after `run-sandbox`

- Update the sandbox execution flow to persist `normalized_state` to `tool_sessions` using context
  `sandbox:{version_id}`.
- Use the existing `update_state(... expected_state_rev=...)` optimistic locking pattern with a small retry on conflict
  (see existing usages in `tools.py`).
- Nice-to-have: include the resulting `state_rev` in the `run-sandbox` response to avoid an extra session fetch
  roundtrip for the UI.

2) Add editor endpoint to read sandbox session state

- Add `GET /api/v1/editor/tool-versions/{version_id}/session` returning `{state, state_rev}` (or `state_rev` only).
- Enforce the same permissions as `run-sandbox`.

3) Add editor endpoint to start a sandbox action

- Add `POST /api/v1/editor/tool-versions/{version_id}/start-action` accepting:
  - `action_id: str`
  - `input: dict[str, JsonValue]`
  - `expected_state_rev: int`
- Handler:
  - loads session state for `sandbox:{version_id}`
  - builds `action.json` bytes `{action_id, input, state}`
  - executes the draft `version_id` in `RunContext.SANDBOX`
  - updates `tool_sessions` with the new normalized state using `expected_state_rev`
  - returns `{run_id, state_rev}`

4) Regenerate SPA OpenAPI types (ADR-0030)

- After adding/changing editor endpoints and response models, regenerate OpenAPI + TypeScript types:
  - `pdm run fe-gen-api-types`

### Frontend (SandboxRunner parity)

1) Render actions

- Import and render `ToolRunActions` in `SandboxRunner.vue`, driven by `runResult.ui_payload.next_actions`.

2) Track `state_rev` (not `state`)

- Add `sandboxStateRev` state.
- After each completed run, fetch `/api/v1/editor/tool-versions/{version_id}/session` to populate `sandboxStateRev`.
- Disable action submission until `sandboxStateRev` is available.

3) Submit actions

- On submit, call the editor start-action endpoint with `expected_state_rev=sandboxStateRev`.
- Surface conflicts (409) as a dedicated action error message (parity with `ToolRunView`).

### Demo tool alignment (html_to_pdf_preview)

With session-scoped file persistence (ADR-0039 / ST-12-05), sandbox action runs receive the original uploaded files in
`/work/input/` alongside `action.json`.

- The demo tool may rely on stable `/work/input/...` paths across sandbox actions.
- The demo tool MUST ignore `action.json` when discovering user-provided input files.

## Test plan

- Manual: run `demo_next_actions.py` and `html_to_pdf_preview.py` in the editor sandbox and verify action loops.
- Automated (recommended): add a focused Playwright check for sandbox next_actions rendering + one action submit.
- Live functional check (REQUIRED for UI/route changes): run backend + SPA dev and verify the editor sandbox flow in a
  browser, then record verification steps in `.agent/handoff.md`.
