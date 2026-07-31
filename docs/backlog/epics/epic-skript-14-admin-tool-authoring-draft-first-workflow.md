---
type: epic
id: EPIC-SKRIPT-14
title: Admin tool authoring (draft-first workflow)
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: active
readiness_review:
  record: inline
  status: not_started
closeout_review:
  record: inline
  status: not_started
outcome: Admins can quickly create draft tools directly from /admin/tools, iterate
  without contributor-only hoops, and publish only when slug and taxonomy are finalized.
retired_ids:
- EPIC-14
---

## Scope

### Source: Scope

- Admin-only draft tool creation directly from `/admin/tools` (bypass suggestion stage).
- Draft placeholder slug convention for admin quick-create: `draft-<tool_id>`.
- Unify suggestion acceptance placeholder slug to `draft-<tool_id>` (single convention for all draft tools).
- Admin-only slug editing for unpublished tools (pre-publish churn support).
- Publish-time guards:
  - reject placeholder slugs (`draft-...`)
  - enforce slug validation + uniqueness
  - block publish until taxonomy is set (at least one profession and one category)
- Keep contributor suggestion flow intact; accepted suggestions still create a draft tool (ADR-SKRIPT-0010), and admins finalize
  slug before publishing.

## Epic Contract

The epic outcome is represented by the scope and stories recorded above.

## ADR Coverage

### Source: References

- Tool editor DX review: `docs/reference/ref-tool-editor-dx-review-2025-12-29.md`

## Contract Inputs

### Source: Dependencies

- ADR-SKRIPT-0037 (tool slug lifecycle)
- EPIC-SKRIPT-19 (proposed): runner I/O + file references foundations (prerequisite for ST-14-24 and ST-14-36)
- Existing editor + metadata/taxonomy panels:
  - ST-11-17 (metadata editor)
  - ST-11-20 (tool taxonomy editor)

## Stories

No separate story list was recorded in the source snapshot.

## Epic Verification Plan

### Source: Implementation Summary (as of 2026-01-15)

- ST-14-09 shipped: `input_schema` is schema-only (never `null`); file picking is represented as a `{"kind":"file"}` field with `min/max`.
- ST-14-10 shipped (foundation-only): shared schema JSON parsing helper + save blocking on invalid schema JSON; schema editor UI actions (prettify/snippets) deferred to ST-14-14.
- ST-14-11/12 shipped: editor run details include stdout/stderr (truncated + caps) and SandboxRunner debug panel exposes copyable JSON/text bundles with missing-details + empty-output states.
- ST-14-13/14 shipped: CodeMirror JSON editors for `settings_schema`/`input_schema` with inline parse diagnostics + preset guidance + prettify + snippet insertion.
- ST-14-15 shipped: backend schema validation endpoint (`POST /api/v1/editor/tools/{tool_id}/validate-schemas`) returns `{valid, issues[]}` and enforces upload limits (`UPLOAD_MAX_FILES`).
- ST-14-16 shipped: debounced backend schema validation UI; shows structured issues per schema and blocks Save + sandbox run when schemas are parseable but backend-invalid.
- ST-14-17 shipped: version diff viewer (virtual file tabs) with copy/download + unified patch support and access-aware errors.
- ST-14-18 shipped: compare defaults + deep links (compare + field), clarified boot contract (`parent_version_id` + `create_draft_from_version_id` + version reviewed/published metadata), and save CTA copy (“arbetsversion”).
- ST-14-30 shipped: IndexedDB-backed working copy persistence with restore prompt, rolling/manual checkpoints, local history drawer, and compare-against-working support.
- ST-14-31 shipped: focus mode toggle hides the desktop sidebar and persists per user, with editor + top-bar controls.
- ST-14-19 shipped: `skriptoteket_toolkit` is the canonical runner helper API for inputs/settings/actions/state, with docs + updated starter template and AI KB.
- ST-14-20 shipped: editor intelligence now treats `skriptoteket_toolkit` as first-class (import completions + hover docs + best-practice lints) and fixes the `outputs` false-positive for list variables.
- ST-14-23 shipped: `next_actions[].prefill` supported (validated + deterministic stripping with system notice), and the SPA renders action forms with initial prefill values.
- `PR-0359` backlog cleanup repaired the remaining stale editor/platform rows on
  2026-06-18. `ST-14-24` is now `done`: first-class file refs ship through
  `/api/v1/tools/{tool_id}/file-refs`, `/api/v1/editor/tool-versions/{version_id}/file-refs`,
  `ToolFileFieldPicker.vue`, `UiActionFieldFileRef.vue`, and the shared
  resolver-backed request manifest path. `ST-14-36` is now `done`: the user
  vault ships through `/api/v1/vault`, `VaultPanel.vue`, vault save/delete/
  restore/download handlers, and `vault:*` resolver support. `ST-14-38` is now
  `done`: `/editor` uses `EditorHubView.vue` and `EditorToolMenu.vue` for MRU
  reopen, compact picking, bounded search, and the governed
  `Kodredigerare`/`Kodredigeraren` labels.
- `PR-0053`, `PR-0054`, `PR-0055`, `PR-0056`, and `PR-0058` are now repaired
  to `done` because their planned UI/backend surfaces are present in the current
  repo. `PR-0056` stays credited as a bounded shared-primitive slice under
  `ST-SKRIPT-14-22`; the parent story remains outside this cleanup batch.
- `ST-14-25` through `ST-14-28` are now canceled as generic
  `layout_editor_v1` backlog lanes. The repo retains historical contract/code
  references, but current classroom layout/seating product value moved into the
  bespoke Klassrumskartan architecture rather than a generic tool-output
  renderer lane.

## Exceptions And Follow-Ups

### Source: Out of scope

- Post-publish slug renames, slug aliases, or redirects (explicitly deferred).
- Tool deletion UX (scrapped tools remain unpublished).
- Public/internal slug differentiation (no extra slug fields).

## Risks

### Source: Risks

- Slug validation/publish guards can block publishing of existing draft tools until slugs/taxonomy are fixed.
  - This is expected and should surface as actionable validation errors for admins.

## Notes

### Source: Stories

- [ST-14-01: Admin quick-create draft tool](../stories/story-14-01-admin-quick-create-draft-tools.md)
- [ST-14-02: Draft slug edit + publish guards](../stories/story-14-02-draft-slug-edit-and-publish-guards.md)
- [ST-14-03: Editor sandbox next_actions parity](../stories/story-14-03-sandbox-next-actions-parity.md)
- [ST-14-04: Editor sandbox input_schema form preview](../stories/story-14-04-sandbox-input-schema-form-preview.md)
- [ST-14-05: Editor sandbox settings parity](../stories/story-14-05-editor-sandbox-settings-parity.md)
- [ST-14-06: Editor sandbox preview snapshots](../stories/story-14-06-editor-sandbox-preview-snapshots.md)
- [ST-14-07: Editor draft head locks](../stories/story-14-07-editor-draft-head-locks.md)
- [ST-14-08: Editor sandbox settings isolation](../stories/story-14-08-editor-sandbox-settings-isolation.md)
- [ST-14-09: Editor input_schema modes (remove null vs [] footgun)](../stories/story-14-09-editor-input-schema-modes.md)
- [ST-14-10: Editor schema JSON guardrails (shared parsing + save blocking)](../stories/story-14-10-editor-schema-json-qol.md)
- [ST-14-11: Editor sandbox run debug details API (stdout/stderr, gated)](../stories/story-14-11-editor-sandbox-run-debug-details-api.md)
- [ST-14-12: Editor sandbox debug panel UX (copyable diagnostics)](../stories/story-14-12-editor-sandbox-debug-panel.md)
- [ST-14-13: CodeMirror JSON editor for tool schemas](../stories/story-14-13-editor-schema-editor-json-codemirror.md)
- [ST-14-14: Schema editor snippets + inline diagnostics UX](../stories/story-14-14-editor-schema-editor-snippets-and-diagnostics.md)
- [ST-14-15: API endpoint to validate tool schemas (settings_schema/input_schema)](../stories/story-14-15-editor-schema-validation-endpoint.md)
- [ST-14-16: Editor UX for structured schema validation errors](../stories/story-14-16-editor-schema-validation-errors-ux.md)
- [ST-14-17: Editor version compare/diff view (code + schemas + instructions)](../stories/story-14-17-editor-version-diff-view.md)
- [ST-14-18: Reviewer navigation improvements (compare targets + deep links)](../stories/story-14-18-editor-review-navigation-and-compare.md)
- [ST-14-31: Editor: Focus mode (collapse left sidebar)](../stories/story-14-31-editor-focus-mode-collapse-sidebar.md)
- [ST-14-19: Runner toolkit helper module (inputs/settings/actions)](../stories/story-14-19-runner-toolkit-helper-module.md)
- [ST-14-20: Editor intelligence updates for toolkit (completions/hover/lints)](../stories/story-14-20-editor-intelligence-toolkit-support.md)
- [ST-14-21: Tool run actions remember prior inputs (sticky action forms)](../stories/story-14-21-tool-run-actions-sticky-inputs.md) (canceled; superseded by ST-14-23)
- [ST-SKRIPT-14-22: Tool run UX conventions for progress + input file references](../stories/story-14-22-tool-run-ux-progress-and-file-references.md)
- [ST-14-23: UI contract v2.x: action defaults/prefill](../stories/story-14-23-ui-contract-action-defaults-prefill.md)
- [ST-14-24: UI contract v2.x: first-class file references](../stories/story-14-24-ui-contract-file-references.md)
- [ST-SKRIPT-14-37: UI output: vega_lite charts (restricted, enabled for all tools)](../stories/story-14-37-ui-output-vega-lite.md)
- [ST-14-25: UI contract v2.x: layout editor output (layout_editor_v1)](../stories/story-14-25-ui-contract-layout-editor-v1-output.md)
- [ST-14-26: UI renderer: layout editor v1 (click-to-assign + apply)](../stories/story-14-26-ui-renderer-layout-editor-v1-click-assign.md)
- [ST-14-27: Layout editor v1: drag/drop interactions (library-based)](../stories/story-14-27-layout-editor-v1-drag-drop.md)
- [ST-14-28: Layout editor v1: UX polish + accessibility + tests](../stories/story-14-28-layout-editor-v1-ux-polish-and-a11y.md)
- [ST-SKRIPT-14-29: Editor: Pro mode combined bundle view (tool.py + schemas)](../stories/story-14-29-editor-pro-mode-combined-bundle-view.md)
- [ST-14-30: Editor: working copy persistence (IndexedDB) + checkpoints + restore](../stories/story-14-30-editor-working-copy-persistence-indexeddb.md)
- [ST-SKRIPT-14-32: Editor: cohesion pass (panel language + input selectors across modes)](../stories/story-14-32-editor-cohesion-pass-input-selectors.md)
- [ST-SKRIPT-14-33: Script bank curation + group generator tool](../stories/story-14-33-script-bank-curation-and-group-generator.md)
- [ST-SKRIPT-14-34: Settings suggestions from tool runs](../stories/story-14-34-settings-suggestions-from-tool-runs.md)
- [ST-SKRIPT-14-35: Tool datasets: per-user CRUD + picker](../stories/story-14-35-tool-datasets-crud-and-picker.md)
- [ST-14-36: User file vault: reusable uploads + picker](../stories/story-14-36-user-file-vault-and-picker.md)
- [ST-SKRIPT-14-39: Cloudflare R2-backed Mina filer storage migration](../stories/story-14-39-cloudflare-r2-backed-mina-filer-storage-migration.md)

Note: File-ref pickers (ST-14-24) and the vault picker (ST-14-36) must support default vault file refs in tool
settings and action prefill (preselect when available; show validation error when missing).

## Decision And Assumption Ledger

The source snapshot is the governing record for the decisions and assumptions stated above.

## Plan Document Review

No separate plan document review was recorded in the source snapshot.

## Epic Closeout Review

No separate closeout review was recorded in the source snapshot.
