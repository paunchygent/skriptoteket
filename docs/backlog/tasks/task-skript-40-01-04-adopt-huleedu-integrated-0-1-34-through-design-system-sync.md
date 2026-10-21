---
type: task
id: TASK-SKRIPT-40-01-04
title: Adopt huleedu-integrated 0.1.34 through design-system sync
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-10-19'
status: in_progress
closeout_review:
  record: inline
  status: not_started
task_kind: story
acceptance_criteria:
- Running repository-governance-frontend-catalog design-system sync from skill-repository main 5cbfeb7f sets design-system-map.json and the mirror to 0.1.34, and the diff holds only what 0.1.34 changed
- UiSegmentedToggle.vue matches the 0.1.34 export byte for byte, with no cast or non-null assertion (the FocusableButton alias is retained as the focus guard's narrow type)
- pdm run design-system-validate, frontend typecheck, ESLint, build and the focused UiSegmentedToggle specs pass
dependencies:
- TASK-SKILL-REP-0351
story: ST-SKRIPT-40-01
backlog_document_profile: contract-derived
---

## Implementation Contract

User request 2026-10-19: release the new shared package and pin all consumers
to the new release. TASK-SKILL-REP-0351 released huleedu-integrated 0.1.34 on
skill-repository main 5cbfeb7f. Skriptoteket mirrored 0.1.33, synced in
2ca0e4a0 under TASK-SKRIPT-40-04-17.

- 0.1.34 changes only `UiSegmentedToggle.vue`: `setButtonRef` takes the raw ref
  value and keeps it only when an `isFocusableButton` guard accepts it. The
  `as FocusableButton | null` cast and the `props.options[index]!` assertion
  are gone. The `FocusableButton` alias is retained: 0.1.34 keeps it as the
  `isFocusableButton` guard's narrow type. There is no visual change.
- This is a version-only refresh: the root map's export set is unchanged, the
  pre-commit hook stays active, and sync updates the version (40-01-01
  adoption rule).
- Adopt through the shared sync only, run from the skill-repository checkout at
  5cbfeb7f with `--consumer-root` set to this worktree. No hand copying.

## Contract Inputs

- TASK-SKILL-REP-0351 (skill-repository main 5cbfeb7f, closeout feb2ff1e).
- Consumer Adoption in skill-repository
  `docs/reference/ref-skill-general-frontend-design-system-resource-package-contract.md`.

## Core Vertical And Performance

A typing change inside one mirrored component; no behaviour, API or
presentation change.

## Validation

- `pdm run design-system-validate`, `pdm run fe-type-check`, `pdm run fe-lint`,
  `pdm run fe-build`.
- The focused Vitest specs that exercise `UiSegmentedToggle`, including its
  keyboard spec.
- No staging walk: the change has no visual or behavioural effect, and the
  user's staging-walk scope covers the exam converter only (2026-10-17).

## Stop Conditions

- Sync touches any file beyond the map, mirror manifest, mirror package.json
  and `UiSegmentedToggle.vue`: stop and report before a full frontend suite.

## Decided Contract Terms

| ID  | Decided contract term |
| --- | --------------------- |
| D1  | Adoption runs through `repository-governance-frontend-catalog design-system sync` against skill-repository main 5cbfeb7f; no hand copy (40-01-01 rule). |
| D2  | Version-only refresh: the export map and pre-commit hook stay as they are. |
| D3  | Proof is design-system validate, typecheck, ESLint, build and the focused `UiSegmentedToggle` specs; a full frontend suite runs only if sync touches more than the one component (orchestrator 2026-10-19). |
| D4  | No staging walk for this task: no visual change, and the staging-walk scope is the exam converter only (user 2026-10-17). |

## Resume here

- 2026-10-19: sync from skill-repository 5cbfeb7f changed exactly four files:
  `design-system-map.json`, the mirror `manifest.json` and `package.json`
  (version and the toggle digest), and `UiSegmentedToggle.vue`, which matches
  the 0.1.34 export byte for byte. `design-system-validate`, `fe-type-check`,
  `fe-lint` and `fe-build` exit 0. Focused Vitest: `UiSegmentedToggle.keyboard.spec.ts`
  (11), `sharedSegmentedToggle.spec.ts` (2) and `PlannerRulesMapCanvas.spec.ts`
  (11) pass, 24 tests. Logs: retained session
  01a15604-06b5-7d32-8594-c25940728f5d `evidence/proof/`.
- Next: independent review, routed by the orchestrator.

## Progress

### Reconciliation 2026-10-20 (Mac parent, against main 114ca971)

- Merged to main as `e9983e4f` (2026-10-19); huleedu-integrated 0.1.34 is pinned. Owed: the independent review, then closeout.

### Fix 2026-10-21 (review findings F1, F2)

- Independent review 2026-10-21 (retained session `01a15f48-0f71-77ba-b7df-f48c8e838efb`
  `evidence/reviews/task-skript-40-01-04-code-review.md`, verdict `changes_requested`)
  raised medium findings F1 (unchecked `EditorWorkspaceMode` assertion in
  `EditorWorkspaceModeSelector.vue`) and F2 (positional DOM selection and
  `HTMLElement` cast in `sharedSegmentedToggle.spec.ts`), and noted this doc
  overstated the `FocusableButton` removal.
- F1: caller options now carry mode-typed values and `onSelect` narrows through
  an `isEditorWorkspaceMode` guard; no shared-component fork, new modes, or
  compatibility path. F2: the spec selects radios and labels by role and visible
  text with `instanceof` narrowing; click, opt-in measurement, resize, and
  disconnect assertions retained.
- Corrected the alias sentences above: the alias is retained as the guard's
  narrow type. Task status unchanged.
