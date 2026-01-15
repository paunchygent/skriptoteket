---
type: reference
id: REF-tool-editor-framework-codemap
title: "Tool editor framework codemap (current vs target)"
status: active
owners: "agents"
created: 2026-01-02
updated: 2026-01-02
topic: "tool editor framework"
links:
  - "ADR-0022"
  - "ADR-0024"
  - "ADR-0038"
  - "ADR-0039"
  - "ADR-0044"
  - "ADR-0045"
  - "ADR-0046"
  - "ADR-0047"
  - "REF-tool-editor-dx-review-2025-12-29"
---

## Purpose

A developer-oriented map of the **tool editor framework** in Skriptoteket, covering:

- Current editor flow (SPA + backend) with ASCII diagrams
- The current Tool UI contract v2 schema surface (inputs, actions, outputs, state)
- UI capabilities and where they live in the SPA
- Target-state roadmap derived from ADRs, reference docs, and stories

This doc is descriptive, not prescriptive. It does not introduce new behavior.

## Quick index (code + docs)

### Frontend (SPA)

- Entry route: `frontend/apps/skriptoteket/src/views/admin/ScriptEditorView.vue`
- Workspace (code + schemas + sandbox + drawers):
  `frontend/apps/skriptoteket/src/components/editor/EditorWorkspacePanel.vue`
- Code editor (CodeMirror 6):
  `frontend/apps/skriptoteket/src/components/editor/CodeMirrorEditor.vue`
- Sandbox runner (snapshot preview + actions):
  `frontend/apps/skriptoteket/src/components/editor/SandboxRunner.vue`
- Sandbox actions/results renderer:
  `frontend/apps/skriptoteket/src/components/editor/SandboxRunnerActions.vue`
- Draft lock composable: `frontend/apps/skriptoteket/src/composables/editor/useDraftLock.ts`
- Editor boot/save state: `frontend/apps/skriptoteket/src/composables/editor/useScriptEditor.ts`
- Schema parsing (JSON array):
  `frontend/apps/skriptoteket/src/composables/editor/useEditorSchemaParsing.ts`
- Editor intelligence bundle: `frontend/apps/skriptoteket/src/composables/editor/skriptoteketIntelligence.ts`
- UI output renderers: `frontend/apps/skriptoteket/src/components/ui-outputs/*`
- Action field renderers: `frontend/apps/skriptoteket/src/components/ui-actions/*`

### Backend (API)

- Editor boot: `src/skriptoteket/web/api/v1/editor/boot.py`
- Draft save/create: `src/skriptoteket/web/api/v1/editor/drafts.py`
- Draft locks: `src/skriptoteket/web/api/v1/editor/locks.py`
- Workflow actions: `src/skriptoteket/web/api/v1/editor/workflow.py`
- Sandbox run + actions: `src/skriptoteket/web/api/v1/editor/sandbox.py`
- Sandbox settings: `src/skriptoteket/web/api/v1/editor/sandbox_settings.py`
- Run details + artifact download: `src/skriptoteket/web/api/v1/editor/runs.py`
- Editor models: `src/skriptoteket/web/api/v1/editor/models.py`

### Domain + infra

- Tool UI contract v2 models: `src/skriptoteket/domain/scripting/ui/contract_v2.py`
- UI policy budgets/caps: `src/skriptoteket/domain/scripting/ui/policy.py`
- Input schema models/validation: `src/skriptoteket/domain/scripting/tool_inputs.py`
- Settings schema models/validation: `src/skriptoteket/domain/scripting/tool_settings.py`
- Sandbox snapshots: `src/skriptoteket/infrastructure/db/models/sandbox_snapshot.py`
- Session files: `src/skriptoteket/infrastructure/session_files/*`

### Reference docs (source of truth)

- UI contract v2: `docs/adr/adr-0022-tool-ui-contract-v2.md`
- UI payload + sessions: `docs/adr/adr-0024-tool-sessions-and-ui-payload-persistence.md`
- Sandbox actions: `docs/adr/adr-0038-editor-sandbox-interactive-actions.md`
- Session files: `docs/adr/adr-0039-session-file-persistence.md`
- Sandbox snapshots: `docs/adr/adr-0044-editor-sandbox-preview-snapshots.md`
- Sandbox settings isolation: `docs/adr/adr-0045-sandbox-settings-isolation.md`
- Draft locks: `docs/adr/adr-0046-draft-head-locks.md`
- Layout editor v1 (proposed): `docs/adr/adr-0047-layout-editor-v1.md`
- Tool editor DX review: `docs/reference/ref-tool-editor-dx-review-2025-12-29.md`

## ASCII codemap: current editor flow

```
AUTHOR (contributor/admin)
  |
  v
/admin/tools/:toolId  OR  /admin/tool-versions/:versionId
  |
  v
GET /api/v1/editor/tools/{tool_id}
GET /api/v1/editor/tool-versions/{version_id}
  -> EditorBootResponse
     - tool + versions + selected_version
     - entrypoint + source_code + schemas + usage_instructions
     - save_mode (snapshot | create_draft)
     - draft_head_id + draft_lock
  |
  v
Draft lock heartbeat
POST /api/v1/editor/tools/{tool_id}/draft-lock (force? if admin)
  |
  +--> Edit code + schemas + instructions (SPA)
  |
  +--> Save
       - if save_mode = snapshot (draft):
         POST /api/v1/editor/tool-versions/{version_id}/save
       - if save_mode = create_draft (non-draft):
         POST /api/v1/editor/tools/{tool_id}/draft
       -> redirect_url => reload editor
  |
  +--> Workflow actions
       POST /submit-review | /publish | /request-changes | /rollback
       -> redirect_url => reload editor
  |
  +--> Sandbox preview (snapshot-based)
       POST /api/v1/editor/tool-versions/{version_id}/run-sandbox
         form-data: files + inputs + snapshot payload
         -> run_id + snapshot_id + state_rev
       poll GET /api/v1/editor/tool-runs/{run_id}
       render ui_payload outputs + artifacts
       if next_actions:
         POST /api/v1/editor/tool-versions/{version_id}/start-action
           { snapshot_id, action_id, input, expected_state_rev }
         poll run result
       session files (optional):
         GET /api/v1/editor/tool-versions/{version_id}/session-files?snapshot_id=...
```

## ASCII codemap: target-state editor flow (planned)

```
AUTHOR (contributor/admin)
  |
  v
Editor boot + draft lock (same as current)
  |
  +--> Schema editor v1
       - CodeMirror JSON surfaces
       - Prettify + example snippets
       - Structured validation via new endpoint
       - input_schema always explicit (no null)
  |
  +--> Sandbox preview (same core flow)
       - Debug panel (stdout/stderr, gated)
       - Clear action-level diagnostics + copy bundle
       - Sticky action inputs / defaults (contract v2.x)
       - File references in actions (contract v2.x)
  |
  +--> Review + compare
       - Diff view (code + schemas + instructions)
       - Deep-linkable compare targets
  |
  +--> Pro mode (optional)
       - Combined bundle view: tool.py + schemas
  |
  +--> New output kind: layout_editor_v1
       - Platform-rendered interactive layout editor
       - Click-to-assign + apply action
       - Drag/drop enhancement + a11y polish
```

## Tool UI contract v2: schema index + UI capabilities

### 1) Contract v2 (raw vs stored)

```
ToolUiContractV2Result (raw result.json from runner/curated)
├─ contract_version: 2
├─ status: "succeeded" | "failed" | "timed_out"
├─ error_summary: string | null
├─ outputs[]: UiOutput (see below)
├─ next_actions[]: UiFormAction (see below)
├─ state: object | null
└─ artifacts[]: RunnerArtifact

UiPayloadV2 (stored rendering source of truth)
├─ contract_version: 2
├─ outputs[]
└─ next_actions[]
```

Source: `src/skriptoteket/domain/scripting/ui/contract_v2.py`

Notes:

- `ui_payload` is normalized and stored (ADR-0024) before rendering.
- `state` is persisted in tool sessions and gated by `state_rev` (ADR-0024).

### 2) Input schema (pre-run inputs)

**Type:** `ToolInputSchema = list[ToolInputField]` (domain: `tool_inputs.py`).

**Field kinds:**

- `string`, `text`, `integer`, `number`, `boolean`, `enum`, `file`
- `enum` requires `options[{value,label}]`
- `file` requires `min`, `max`, optional `accept[]`

**Current semantics:**

- `input_schema` is always an array of fields (never `null`)
- File picker is shown only when the schema includes a `file` field:
  - `min=1` => files required
  - `min=0` => files optional
- `input_schema == []` => no pre-run inputs and no file picker
- Only **one** file field is allowed, enforced server-side

**UI renderers:**

- Pre-run inputs: `frontend/apps/skriptoteket/src/components/tool-run/ToolInputForm.vue`
  (via `useToolInputs.ts`)
- Editor sandbox inputs: `SandboxInputPanel.vue`

### 3) Settings schema (per-user settings)

**Type:** `ToolSettingsSchema = list[UiActionField]`

Settings fields are **the same field kinds** as actions:

- `string`, `text`, `integer`, `number`, `boolean`, `enum`, `multi_enum`

**UI renderers:**

- Production: `ToolRunSettingsPanel.vue`
- Sandbox: same component via `useSandboxSettings.ts`

**Isolation:**

- Production context: `settings:{schema_hash}`
- Sandbox context: `sandbox-settings:{draft_head_id + schema_hash}` (ADR-0045)

### 4) Actions + steps (interactive tools)

**Type:** `UiFormAction`

```
UiFormAction
├─ action_id: string
├─ label: string
├─ kind: "form"
├─ fields[]: UiActionField
└─ prefill?: {[field_name]: JsonValue}  (Contract v2.x)
```

Actions are rendered as platform-owned forms and submitted via:

- Production: `POST /api/v1/start-action`
- Sandbox: `POST /api/v1/editor/tool-versions/{version_id}/start-action`

Each action run increments **state_rev** and yields a new run (step).
UI supports step history:

- Production: `ToolRunStepIndicator` in `ToolRunView.vue`
- Sandbox: step buttons in `SandboxRunnerActions.vue`

Prefill notes (ADR-0060):

- Server-side: `prefill` valideras deterministiskt under normalisering; ogiltiga entries strippas och blir en system-notis
  (`src/skriptoteket/domain/scripting/ui/normalizer/_actions.py`, `src/skriptoteket/domain/scripting/ui/normalizer/_notices.py`).
- UI: `prefill` används som initialvärde (skriver inte över användarens egna ändringar) och merge:as deterministiskt per
  fältnamn (`frontend/apps/skriptoteket/src/components/ui-actions/UiActionForm.vue`,
  `frontend/apps/skriptoteket/src/components/tool-run/ToolRunActions.vue`).

### 5) Outputs + artifacts

**Output kinds (current allowlist):**

- `notice` (info|warning|error)
- `markdown`
- `table`
- `json`
- `html_sandboxed`
- `vega_lite` (curated-policy only today)

**UI renderers:** `frontend/apps/skriptoteket/src/components/ui-outputs/*`

- Unknown kinds fall back to `UiOutputUnknown.vue`
- `html_sandboxed` renders inside a sandboxed iframe
- `vega_lite` renderer exists but is policy-gated for curated apps

**Artifacts:** rendered via `ToolRunArtifacts.vue` and downloadable via
`/api/v1/editor/tool-runs/{run_id}/artifacts/{artifact_id}`.

### 6) Policy budgets and caps (current)

Defined in `src/skriptoteket/domain/scripting/ui/policy.py`.

- Default policy: outputs/actions for user-authored tools
- Curated policy: larger caps + `vega_lite`

Key defaults (excerpt):

- `state` max: 64 KiB (default) / 256 KiB (curated)
- `ui_payload` max: 256 KiB (default) / 512 KiB (curated)
- outputs: 50 (default) / 150 (curated)
- next_actions: 10 (default) / 25 (curated)
- fields/action: 25 (default) / 60 (curated)

See ADR-0024 for the full cap list.

## Current editor behavior (functional detail)

### Boot + save modes

- `EditorBootResponse.save_mode` is either:
  - `snapshot`: editing a draft version (save in-place)
  - `create_draft`: editing a non-draft version (save creates new draft)

### Draft locks

- Locks are scoped to the **draft head** (ADR-0046).
- Save, sandbox run, and settings save are blocked without a lock.
- Lock is auto-refreshed by `useDraftLock.ts` heartbeat.

### Sandbox preview (snapshot + actions)

- Sandbox run sends a snapshot payload (entrypoint + source + schemas + instructions).
- Backend persists a snapshot with TTL 24h (ADR-0044).
- `start-action` requires `snapshot_id` + `expected_state_rev` (ADR-0038).
- Session files can be reused/cleared per run (ADR-0039).

### Workflow actions

- Contributor: submit for review
- Admin: publish / request changes
- Superuser: rollback archived version

### Metadata + taxonomy + maintainers

- Metadata: title/summary/slug via `/metadata` and `/slug`
- Taxonomy: `/taxonomy`
- Maintainers: `/maintainers`

These live in drawers to keep the editor workspace focused.

### Editor intelligence + AI support

- Inline completions: `POST /api/v1/editor/completions`
- Edit suggestions: `POST /api/v1/editor/edits`
- Local intelligence (lint/hover/completions):
  `frontend/apps/skriptoteket/src/composables/editor/skriptoteketIntelligence.ts`

See ADR-0035 + ST-08-10/11 for the rule surface.

## Target state (derived from ADRs + stories)

Grouped by area. Story IDs link to backlog details.

### Schema authoring (inputs + settings)

- **ST-14-09 (done)**: remove legacy `input_schema == null` and make file behavior explicit
- **ST-14-10**: JSON QoL (prettify + example snippets)
- **ST-14-13/14**: CodeMirror JSON editor + inline diagnostics
- **ST-14-15/16**: backend validation endpoint + structured UI errors

### Sandbox transparency + debugging

- **ST-14-11**: debug details API (stdout/stderr, truncated, gated)
- **ST-14-12**: Debug panel + copyable diagnostics bundle

### Review + compare

- **ST-14-17**: diff view (code + schemas + instructions)
- **ST-14-18**: compare navigation + deep links

### Editor intelligence + tooling

- **ST-14-20**: toolkit-aware completions/hover/lints

### Pro mode editing

- **ST-14-29**: combined bundle view (tool.py + schemas), validation + recovery

### Contract expansion + interactive UI

- **ST-14-25**: `layout_editor_v1` output kind + normalization
- **ST-14-26**: layout editor renderer (click-to-assign + apply action)
- **ST-14-27/28**: drag/drop + a11y polish + tests

### Contract v2.x enhancements

- **Sprint 2026-06-09**: action defaults + file references in actions
  (`docs/backlog/sprints/sprint-2026-06-09-tool-ui-contract-v2-action-defaults-and-file-refs.md`)

## Appendix: reference map

### ADRs

- ADR-0022: Tool UI contract v2
- ADR-0024: UI payload persistence + sessions
- ADR-0038: Sandbox interactive actions
- ADR-0039: Session file persistence
- ADR-0044: Sandbox preview snapshots
- ADR-0045: Sandbox settings isolation
- ADR-0046: Draft head locks
- ADR-0047: Layout editor v1 (proposed)

### Reference docs

- `docs/reference/ref-tool-editor-dx-review-2025-12-29.md`
- `docs/reference/ref-ai-script-generation-kb.md`
- `docs/reference/ref-codemirror-integration.md`

### Sprints (planned)

- `docs/backlog/sprints/sprint-2026-03-03-tool-editor-dx-quick-wins.md`
- `docs/backlog/sprints/sprint-2026-03-17-tool-editor-sandbox-debug-details.md`
- `docs/backlog/sprints/sprint-2026-03-31-tool-editor-schema-editor-v1.md`
- `docs/backlog/sprints/sprint-2026-04-14-tool-editor-schema-validation-v1.md`
- `docs/backlog/sprints/sprint-2026-04-28-tool-editor-version-diff-v1.md`
- `docs/backlog/sprints/sprint-2026-05-12-tool-editor-runner-toolkit-and-intelligence.md`
- `docs/backlog/sprints/sprint-2026-06-09-tool-ui-contract-v2-action-defaults-and-file-refs.md`
- `docs/backlog/sprints/sprint-2026-06-23-tool-layout-editor-v1-contract-and-renderer.md`
- `docs/backlog/sprints/sprint-2026-07-07-tool-layout-editor-v1-drag-and-drop.md`
