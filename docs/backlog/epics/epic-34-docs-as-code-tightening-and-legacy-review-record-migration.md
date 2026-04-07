---
type: epic
id: EPIC-34
title: "Docs-as-code tightening and legacy review-record migration"
status: done
owners: "agents"
created: 2026-04-06
updated: 2026-04-06
outcome: "Skriptoteket has one canonical docs-as-code planning contract: target-based retained review docs govern implementation gates, sprint docs are treated as historical archive rather than a live planning shape, and the remaining legacy duplicate review records are migrated or explicitly retired so docs navigation and validation reflect the same rules."
dependencies:
  - "REF-review-workflow"
  - "REF-sprint-planning-workflow"
---

## Scope

- Backfill the docs-as-code changes already landed in the repo: target-based retained review docs,
  review-template/rule/reference alignment, docs-contract support for review primary targets, and
  sprint-plan retirement.
- Create canonical backlog ownership for those shipped changes instead of leaving them implied only
  through `.agents/handoff.md`, rule updates, and point-in-time review cleanup.
- Migrate the remaining legacy duplicate review families that still reuse the same epic review id
  across multiple files, especially the current `REV-EPIC-08`, `REV-EPIC-14`, and `REV-EPIC-23`
  clusters. `ST-34-02` / `PR-0230` now complete that lane by retargeting the remaining legacy
  records into canonical target-based review docs or explicit historical references.
- Repair index entries, crosslinks, and backlog references so active docs no longer imply bundled
  epic-ledger review gates or live sprint-led planning.
- Keep [REF-review-workflow](../../reference/ref-review-workflow.md) as the governing retained
  review reference attached to this epic and its stories.

## Out of Scope

- Product, runtime, UI, or API behavior changes outside the docs-as-code system.
- Rewriting every historical backlog document that merely mentions a sprint when that mention does
  not conflict with the current planning contract.
- Inventing a new review model beyond the current epic/story/PR target-based retained workflow.
- Deleting historical review records without an explicit migration rationale recorded in the docs.

## Risks

- If legacy review records are split carelessly, the repo could lose the historical decision
  boundaries those docs were meant to retain.
- If index and backlog crosslinks are only partially updated, the repo may continue to imply that
  sprint docs or bundled epic ledgers are current planning surfaces.
- Because part of this epic is backfilled after the fact, the docs must clearly distinguish between
  already-shipped governance changes and the remaining migration work.

## Story Stack

- [ST-34-01: Docs-as-code review workflow cutover and sprint retirement backfill](../stories/story-34-01-docs-as-code-review-workflow-cutover-and-sprint-retirement-backfill.md)
- [ST-34-02: Legacy review-record migration to the target-based model](../stories/story-34-02-legacy-review-record-migration-to-the-target-based-model.md)

## Notes

- This epic is intentionally backfilled after the current docs-as-code tightening already landed in
  the review workflow reference, rule, template, docs contract, validator, and handoff.
- [REF-review-workflow](../../reference/ref-review-workflow.md) is the governing retained-review
  reference for this epic and both child stories.
- `ST-34-01` records the current shipped baseline. `ST-34-02` owned the remaining historical review
  migration and index cleanup lane and is now complete via `PR-0230`.

## Implementation Summary (as of 2026-04-06)

- `REV-EPIC-34` is now approved: the docs-as-code tightening lane has an explicit retained review
  record, and `EPIC-34` is now closed as the canonical owner of the completed review-workflow
  backfill and archive migration lane.
- `ST-34-01` is now backfilled as done to capture the shipped target-based review workflow cutover,
  validator/rule/template alignment, and sprint-doc retirement already present in the repo.
- `ST-34-02` is now complete: `PR-0230` retargeted the remaining legacy review records to the
  canonical target-based model, preserved the historical patch-workflow brief as linked support
  material for `REV-PR-0031`, and repaired the backlog/index/handoff crosslinks.
