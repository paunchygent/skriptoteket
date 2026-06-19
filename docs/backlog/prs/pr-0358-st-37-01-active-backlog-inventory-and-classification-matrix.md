---
type: pr
id: PR-0358
title: "ST-37-01 active backlog inventory and classification matrix"
status: done
owners: "agents"
created: 2026-06-17
updated: 2026-06-17
stories:
  - "ST-37-01"
tags:
  - docs
  - backlog
acceptance_criteria:
  - "Given the repo backlog has many open statuses, when this slice is complete, then there is an inventory artifact listing every active/proposed/ready/in-progress/blocked epic, story, and PR task with current status, parent links, and proposed classification."
  - "Given classification can be destructive if guessed, when a row proposes done, canceled, dropped, or rehome, then it names the code/docs/review/evidence or marks the row `needs-decision`."
  - "Given script/editor work still has value, when those rows are classified, then the matrix separates preserved platform capability from stale front-door product positioning."
---

# PR-0358: ST-37-01 Active Backlog Inventory And Classification Matrix

## Problem

The backlog has accumulated several generations of work. There is no current
single evidence matrix that says which open items are still aligned, already
done, superseded, misplaced, or blocked on a product decision.

## Goal

Create the inventory evidence needed before any status cleanup begins.

## Non-goals

- No mass status changes in this slice.
- No production code or UI changes.
- No deletion of historical docs.

## Implementation plan

1. Enumerate open backlog items under `docs/backlog/epics/`,
   `docs/backlog/stories/`, and `docs/backlog/prs/`.
2. Group them by major product family: script/editor/runner, shell/catalog,
   Klassrumskartan, Conversion Hub/Exam/Transcript/Document, games, auth/ops,
   docs/testing/security, and undecided.
3. Record a classification for each row using
   [REF-current-product-direction-and-backlog-inventory-2026-06-17](../../reference/ref-current-product-direction-and-backlog-inventory-2026-06-17.md).
4. Flag rows that require code verification before state repair.
5. Update `.codex/handoff.md` with a short pointer to the retained inventory
   artifact.

## Test plan

- `pdm run docs-validate`
- `pdm run handoff-validate`
- `git diff --check`

## Rollback plan

Revert the inventory artifact and handoff pointer if the classification model is
rejected during review.

## Implementation Summary

Completed on 2026-06-17. The retained inventory artifact is
[REF-pr-0358-active-backlog-inventory-2026-06-17](../../reference/ref-pr-0358-active-backlog-inventory-2026-06-17.md).
It captures 196 open backlog rows: 22 epics, 68 stories, and 106 PR tasks. The
matrix classifies rows as `keep-active`, `needs-decision`,
`done-state-repair`, `split-or-rehome`, `superseded-cancel`, or `drop-epic`,
with evidence keys and a recommended first cleanup queue for `PR-0359`.

After review feedback on 2026-06-17, the artifact was amended with a deep audit
revision that vets each major domain set against current code and newer
done-state backlog evidence. That revision supersedes the first-pass
classification counts for `PR-0359` cleanup decisions.

## Verification

- `pdm run docs-validate`
- `pdm run handoff-validate`
- `git diff --check`
