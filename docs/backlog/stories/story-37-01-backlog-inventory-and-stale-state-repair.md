---
type: story
id: ST-37-01
title: "Backlog inventory and stale-state repair"
status: done
owners: "agents"
created: 2026-06-17
updated: 2026-06-18
epic: "EPIC-37"
dependencies:
  - "REF-current-product-direction-and-backlog-inventory-2026-06-17"
  - "REV-EPIC-37"
acceptance_criteria:
  - "Given the backlog contains old active/proposed/ready/in-progress/blocked items, when the inventory pass runs, then every touched epic, story, and PR task receives an evidence-backed classification of keep-active, done-state-repair, superseded-cancel, drop-epic, split-or-rehome, or needs-decision."
  - "Given a backlog item is already done in code or docs, when it is classified, then its status is repaired to `done` only with named implementation, proof, or review evidence."
  - "Given a backlog item is obsolete, when it is classified, then the docs mark it `canceled` or `dropped` with the later architecture/product decision that superseded it and any preserved follow-up value."
  - "Given script creation and runner work are no longer the only product center, when those items are audited, then valuable editor/runner/governance capabilities are preserved unless they are specifically superseded by current code or product decisions."
---

# ST-37-01: Backlog Inventory And Stale-State Repair

## Context

The backlog now contains several generations of product direction: script
creation and running, full SPA migration, tool authoring, catalog/personalization
work, Klassrumskartan, Conversion Hub, Exam Converter, transcript workflows, and
games. Many items remain `active`, `ready`, `in_progress`, `blocked`, or
`proposed` even though later work may have completed, superseded, or rehomed
them.

This story is the first step. It prevents later UI and app-presentation work
from building on stale backlog signals.

## Planned PR Slices

- [x] [PR-0358: ST-37-01 active backlog inventory and classification matrix](../prs/pr-0358-st-37-01-active-backlog-inventory-and-classification-matrix.md)
- [x] [PR-0359: ST-37-01 stale-state repair and supersession cleanup batch](../prs/pr-0359-st-37-01-stale-state-repair-and-supersession-cleanup-batch.md)

## Notes

- This is not a purge. It is a truth-maintenance pass.
- Keep historical docs when they still explain why the repo moved. Change status
  and crosslinks before deleting anything.
- When an item is valuable but misplaced, prefer `split-or-rehome` over
  cancelation.
- `PR-0358` is complete through
  [REF-pr-0358-active-backlog-inventory-2026-06-17](../../reference/ref-pr-0358-active-backlog-inventory-2026-06-17.md).
  The artifact now contains a post-review deep audit revision that supersedes
  the first-pass classification counts. `PR-0359` should start with the revised
  evidence-backed repair queue listed there and leave `needs-decision` rows
  untouched until product direction closes them.
- `EPIC-37` remains `proposed` and `REV-EPIC-37` remains pending. The
  2026-06-18 `PR-0359` cleanup batch records the requested docs-only state
  repairs but does not replace the epic review gate.
- `PR-0359` completed the first cleanup batch on 2026-06-18 and was approved by
  [REV-PR-0359](../reviews/review-pr-0359-stale-state-repair-and-supersession-cleanup-batch.md).
  Done-state repairs were applied where current code/docs evidence supported
  them, clear superseded browser-auth and generic `layout_editor_v1` rows were
  canceled with successor notes, and rows with remaining acceptance gaps were
  left open with rationale recorded in `PR-0359`.

## Implementation Summary

`ST-37-01` is complete as of 2026-06-18. `PR-0358` produced the retained
inventory/deep-audit artifact, and `PR-0359` applied the first reviewed
docs-only status repair/supersession cleanup batch. Remaining product-lane,
Sir Convert boundary, service-shell, and app-presentation work continues under
`ST-37-02`, `ST-37-03`, and `ST-37-04`; `EPIC-37` itself remains proposed until
`REV-EPIC-37` is approved.
