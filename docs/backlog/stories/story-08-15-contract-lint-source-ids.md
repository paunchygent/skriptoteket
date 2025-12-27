---
type: story
id: ST-08-15
title: "Contract lint: stable source IDs + clean tooltips (AI signal)"
status: ready
owners: "agents"
created: 2025-12-27
epic: "EPIC-08"
acceptance_criteria:
  - "Given Contract v2 linting finds a violation, when diagnostics are emitted, then each contract diagnostic includes a stable `source` ID (e.g. `ST_CONTRACT_OUTPUTS_NOT_LIST`)"
  - "Given a contract diagnostic has severity error or warning, when the lint tooltip is shown, then the source label row is hidden (clean tooltip) while the diagnostic still includes `source` in code"
  - "Given existing Swedish lint messages, when this story is implemented, then the message texts remain unchanged"
ui_impact: "Keeps lint tooltips clean while exposing stable machine-readable rule IDs for future AI/telemetry."
data_impact: "None - client-side only."
dependencies: ["ST-08-11", "ST-08-12"]
---

## Context

Today, contract diagnostics are emitted without `Diagnostic.source`. That means humans can read the Swedish message, but
future features (AI inline/block suggestions, telemetry, quick-fix mapping) would need to infer rule identity from
message text, which is brittle.

## Scope

### Add stable rule IDs (`Diagnostic.source`)

In `contractDiagnostics(...)` in `frontend/apps/skriptoteket/src/composables/editor/skriptoteketLinter.ts`, set
`source` for each contract diagnostic, using the IDs already documented in ST-08-11:

- `ST_CONTRACT_KEYS_MISSING`
- `ST_CONTRACT_OUTPUTS_NOT_LIST`
- `ST_CONTRACT_OUTPUT_KIND_MISSING`
- `ST_CONTRACT_OUTPUT_KIND_INVALID`
- `ST_NOTICE_FIELDS_MISSING`
- `ST_NOTICE_LEVEL_INVALID`

(Optionally also add a `source` for the "dynamic return" hint.)

### Hide the source row in tooltips for error/warning

Keep `source` in the diagnostic object for machine consumption, but hide the visual source label row in the tooltip for
`severity: error` and `severity: warning` (so tooltips stay user-focused).

Implementation note: do this via a minimal CodeMirror theme/CSS override targeting the lint tooltip source element
(`.cm-diagnosticSource`) inside error/warning diagnostics.

## Out of Scope

- Quick-fix actions
- Changing lint severities
- Rewriting message texts

## Files

### Modify

- `frontend/apps/skriptoteket/src/composables/editor/skriptoteketLinter.ts`
- `frontend/apps/skriptoteket/src/components/editor/CodeMirrorEditor.vue` (or another existing global CSS/theme entry point)
