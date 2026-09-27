---
type: task
id: TASK-SKRIPT-40-01-02
title: Adopt the shared dense components, SystemMessage and ToastHost
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-09-27'
status: proposed
closeout_review:
  record: inline
  status: not_started
task_kind: story
acceptance_criteria:
- All shared Vue exports including dense primitives, action/icon/status components, spinner, toggle, SystemMessage, ToastHost, glyph table/components and barrel are synced into the package-shaped shared subtree with no superseded local implementation remaining
- The released catalog peer and complete import closure let this task build independently of 0187; local-only components remain behind the local composition barrel
- Nullable-string SystemMessage text, hiding, dismissal, clear handlers and failure announcements are preserved through the released API and explicit consumer adaptation
- Toasts render newest-first through a bottom-placement local adapter around the unchanged store, with correct eviction, dismissal and expiry
- Frontend typecheck, unit tests, build and shared design-system validation pass, clean-state repeat sync changes no file, and the touched workflows pass the governed Hemma staging walk
dependencies:
- TASK-SKRIPT-40-01-01
story: ST-SKRIPT-40-01
backlog_document_profile: contract-derived
---

## Implementation Contract

Adopt the complete released Vue runtime from 0186. Use the following exact
export map under prefix `frontend/apps/skriptoteket/src/components/ui/shared/`:

| Export id | Target relative to prefix |
| --- | --- |
| dense-tool-primitives | denseToolPrimitives.ts |
| ui-glyphs | uiGlyphs.ts |
| vue-barrel | index.ts |
| ui-dense-action-button | components/UiDenseActionButton.vue |
| ui-dense-icon-button | components/UiDenseIconButton.vue |
| ui-dense-status-pill | components/UiDenseStatusPill.vue |
| ui-dense-spinner | components/UiDenseSpinner.vue |
| ui-segmented-toggle | components/UiSegmentedToggle.vue |
| system-message | components/SystemMessage.vue |
| toast-host | components/ToastHost.vue |
| ui-glyph | components/UiGlyph.vue |
| ui-symbol | components/UiSymbol.vue |

Keep 01-01's three target paths and mirror. Action-buttons remains null until
01-03; brand and auth-lifecycle stay null. Install the released `@lucide/vue`
peer (0186 expects 1.47.0) through the frontend catalog and update the lock
before frontend validation. The old peer remains only for unmigrated callers
until Story 2; this task does not depend on 0187.

Keep `src/components/ui/index.ts` local: re-export `./shared` and explicitly
export local-only components/types. Remove superseded flat package-component,
spinner and primitive implementations. Migrate every direct value/type/test
import, including imports in remaining local components. Do not leave
same-name local exports shadowing package exports or rewrite synced imports.

SystemMessage adaptation:

- Use the released optional `modelValue?: string | null`, default undefined. Undefined preserves slot-only rendering; null and empty string hide; nonempty strings show. Default slot overrides escaped model-text fallback.
- Rename variant to tone and error to failure, including dynamic values. Replace SystemMessageVariant imports/types with exported SystemMessageTone; preserve narrower info/warning types where appropriate.
- Package dismissible defaults false. Explicitly opt in wherever the former consumer default true applied; preserve explicit false/dynamic bindings and dismissLabel (default Stäng).
- Preserve nullable-string v-model and existing update:modelValue clear handlers. Dismiss emits null update then dismiss once each; do not wire duplicate clear effects.
- Failure messages explicitly supply role=alert, aria-live=assertive and aria-atomic=true on the root; other tones supply status/polite/true. Dynamic tones compute these together. Preserve IDs, slots and custom labels. HuleEdu defaults are not changed to achieve these consumer semantics.

Add local `src/components/ui/SkriptoteketToastHost.vue`, distinct from the
package export. Derive a reversed copy of useToastStore().toasts, pass it to
package ToastHost with placement=bottom, and forward dismiss by id to the
store. Preserve existing responsive/safe-area placement through the host's
custom properties and keep any teleport in the wrapper. Replace App.vue's
store-owned host with this adapter. Do not change the store, timers or
useToast call sites or recreate the old inner toast styling.

Use 01-01's admitted clean-map checkpoint sequence for this expansion; restore
the automatic hook, validate and parent-commit the coherent synced/adapted
result before the no-diff repeat sync.

## Contract Inputs

- Retained plan `.orchestration/context/sessions/01a0e42e-f433-727d-a17f-f9eced6d04bc/evidence/planning/TASK-SKRIPT-REP-0033/plan.md`, D9-D12/D16 and admitted D19-D22/D24-D25.
- TASK-SKRIPT-40-01-01; admitted 0186 SystemMessage/spinner release contract and HuleEdu evidence.
- EPIC-SKRIPT-40 review R1-R4/R6 and the inspected package import graph.

## Core Vertical And Performance

Planner share actions render secondary/busy states with the shared spinner;
modal/panel helpers and equal-width toggles preserve behavior. AdminTools
shows model-only error text and clears it; ChatDrawer clear handlers still
work. The adapter renders ordered multiple toasts with unchanged timers.

No per-meaning bundle pruning is assumed. Retain production-build output
before/after this runtime adoption to expose temporary dual-peer/table costs;
there is no numerical size gate. Equal-width observation runs only when opted
in and preserves the existing bounded resize-driven behavior.

## Validation

- Resolve every adopted relative import, including spinner and barrel dependencies; no missing target or peer. Run `pdm run fe-type-check`, `pdm run fe-test`, `pdm run fe-build` and `pdm run design-system-validate` without 0187.
- Focused message tests cover omitted model/rich slots, text-only model, slot precedence, empty/null hide and later show, every tone, explicit default dismissal, false/dynamic dismissal, null/update/dismiss sequence, IDs/labels/ARIA, AdminTools v-model and ChatDrawer clear handlers.
- Focused toast tests assert input C/B/A for store A/B/C without store mutation; adding D evicts A and renders D/C/B; dismiss by id and fake-timer expiry remove only intended entries.
- Test busy spinner/disabled/accessibility behavior and equal-width toggle behavior. Shared defaults remain unchanged when promoted props are absent.
- Record real sync/validation and clean committed no-diff repeat sync with automatic hook active.
- Hemma staging walk: planner/share actions, modal/drawer, segmented toggle, a real error and its dismissal, and a visible multi-toast bottom stack. Use governed HuleEdu browser-session helpers/preflight.

## Stop Conditions

- Stop if the release lacks any required prop, event, exported type, spinner export, peer or transitive import; route the missing promotion upstream instead of patching synced files.
- Stop on unapproved map checkpoint or failed digest/import/frontend checks. No adoption depends on a future 0187 repair.

## Decided Contract Terms

| ID | Decided contract term |
| --- | --- |
| D1 | Adopt the complete shared Vue dependency closure including spinner and released glyph runtime/peer. Source: retained D11/D20/D25; R1. |
| D2 | Messages use tone, nullable-string model, slot fallback, explicit consumer dismissal and failure ARIA. Source: retained D12/D21; R3. |
| D3 | Toast adapter derives newest-first props and bottom placement; store and timers stay unchanged. Source: retained D10/D22; R4. |
| D4 | Shared subtree has a local composition barrel and migrated direct imports; no local forks. Source: retained D19; R2. |
| D5 | Parent-owned clean-map/result/repeat proof applies with the automatic hook restored. Source: retained D24; R6. |
