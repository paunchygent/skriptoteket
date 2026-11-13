---
type: task
id: TASK-SKRIPT-REP-0014
title: 'Klassrumskartan: fundamentals contract split, draft lifecycle, and saved artifacts'
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: ready
readiness_review:
  record: inline
  status: not_started
closeout_review:
  record: inline
  status: not_started
task_kind: repository
acceptance_criteria:
- 'The fundamentals contract is class-first: the class becomes the main workspace
  anchor and classrooms become secondary reusable context.'
- Draft lifecycle is server-owned and class-scoped, with one active grouping draft
  and one active seating draft per class.
- Planner navigation and API surfaces are split by teacher task and draft kind, so
  grouping and seating stop sharing one default whole-workspace randomize/save contract.
- Frontend planner state is organized into a normalized workspace core plus grouping,
  seating, and advanced slices, and autosave patches only the dirty slice instead
  of rewriting the whole workspace on every save.
- Draft revision checks are enforced atomically in the write path, and mode-specific
  save flows no longer rely on a non-atomic pre-check plus full child-collection replacement.
- Named saved groupings and seating arrangements use class-owned root records plus
  immutable revisions, store only mode-relevant payloads/settings, and project into
  the vault without making the vault the source of truth.
- Deleting a class or classroom is blocked safely or handled via a retention-safe
  policy when active drafts still depend on it.
- The planner web layer is brought back into repo standards by removing forbidden
  router-module patterns and depending on application protocols rather than concrete
  handler classes at the web boundary.
dependencies:
- ADR-SKRIPT-0071
- ADR-SKRIPT-0072
---

## Context

### Source: Problem

EPIC-24, ADR-SKRIPT-0071, and the revised review now describe the right product direction, but several
important implementation-shaping rules from the architectural review still need a dedicated
technical contract before coding starts.

The current planner remains too whole-workspace-oriented:

- the teacher-facing launch model is still too symmetric between class and classroom
- mode separation is not yet strong enough in routing, API shape, and store boundaries
- draft resume is too client-local
- autosave remains broader and less atomic than the fundamentals workflow should allow
- named saved outputs still need a dedicated persistence and revision model
- asset deletion and router-boundary cleanup still need explicit implementation policy

At the same time, the current backend layering is mostly good and should be preserved:

- pure domain modules for rule logic
- application handlers orchestrating repositories and UoW
- curated-app bespoke endpoints
- repositories flushing rather than committing

## Impact And Escalation

This is a repository-governance task; no product behavior is authorized by this task.

## Decision And Assumption Ledger

The source does not record a separate decision and assumption ledger.

## Plan

### Source: Implementation plan

- Frontend state:
  - split planner state into workspace core + grouping slice + seating slice + advanced slice
  - keep normalized planner structures, but stop consuming them through one everything-store and one blended draft mental model in the default UI
  - keep the debounce, but send only dirty-slice patches
- Frontend navigation:
  - move from a symmetric launch gate to a class-first workspace
  - make planner mode route-level (`groups` / `seats`) rather than only local shell state
  - keep the landing page as the default route and make resume explicit
- Backend draft lifecycle:
  - add lifecycle/status semantics for class-scoped drafts and a resolve flow for compatible active drafts
  - enforce one active draft per class per draft kind
  - prevent silent accumulation of orphaned mutable drafts
- Backend write path:
  - move optimistic concurrency to atomic compare-and-swap at the database write boundary
  - stop defaulting to whole-workspace child-collection replacement for every autosave
- Backend planner APIs:
  - add class-first entry surfaces plus mode-specific read/write/randomize/save surfaces for grouping and seating
  - keep advanced validation/suggestion/finalize endpoints separate from the fundamentals workflow
- Saved outputs:
  - introduce class-owned saved roots plus immutable revisions
  - keep saved grouping payloads grouping-focused and saved seating payloads seating-focused
  - sync vault projections after planner persistence succeeds
- Safety / cleanup:
  - block or safely retain class/classroom records that still back active drafts
  - clean router/web boundary drift so the API layer matches repo rules

## Implementation Steps

The source does not provide separate implementation steps.

## Proof

### Source: Test plan

- Docs:
  - `pdm run docs-validate`
- Frontend:
  - route-level mode navigation tests
  - workspace/store-slice unit tests
  - autosave conflict coverage for slice-specific patching
- Backend:
  - draft resolve/lifecycle tests
  - atomic revision conflict tests
  - grouping/seating endpoint contract tests
  - saved-artifact revision tests
  - delete-while-draft-active policy tests
- Manual:
  - live landing-page -> planner -> back flow
  - explicit resume affordance check
  - group-only randomize/save and seating-only randomize/save smoke checks

## Validation

### Source: Test plan

- Docs:
  - `pdm run docs-validate`
- Frontend:
  - route-level mode navigation tests
  - workspace/store-slice unit tests
  - autosave conflict coverage for slice-specific patching
- Backend:
  - draft resolve/lifecycle tests
  - atomic revision conflict tests
  - grouping/seating endpoint contract tests
  - saved-artifact revision tests
  - delete-while-draft-active policy tests
- Manual:
  - live landing-page -> planner -> back flow
  - explicit resume affordance check
  - group-only randomize/save and seating-only randomize/save smoke checks

## Stop Conditions

### Source: Non-goals

- Implementing the visible advanced solver UI.
- Reintroducing whole-workspace finalize/snapshot as the teacher-facing save button behavior.
- Delivering PDF/XLSX export.
- Expanding student metadata or rule-tuning surfaces in the default planner.

## Lessons Learned

### Source: Status note (2026-03-31)

`EPIC-24` and `ST-24-01` through `ST-24-04` are already closed through later narrower slices, so
this document now reads more like an umbrella contract than a clearly pending implementation task.
Its `ready` status is left unchanged here pending an explicit close-or-supersede decision.

## Notes

### Source: Rollback plan

- Revert the contract-shaping implementation PR if it destabilizes the planner workflow.
- Leave the fundamentals docs in place and reopen the technical PR as a narrower follow-up if the
  implementation needs to be decomposed further.

## Readiness

The source does not include a separate readiness record.

## Closeout

The source does not include a separate closeout record.
