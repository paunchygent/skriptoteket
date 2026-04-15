---
type: story
id: ST-34-01
title: "Docs-as-code review workflow cutover and sprint retirement backfill"
status: done
owners: "agents"
created: 2026-04-06
epic: "EPIC-34"
dependencies:
  - "REF-review-workflow"
  - "REF-sprint-planning-workflow"
acceptance_criteria:
  - "Given the repo now uses a retained review model, when authors create or update review docs, then epic/story/PR target-based review records, primary-target id rules, and governed `adrs:` usage are documented consistently across `REF-review-workflow`, the review template, the review rule, the docs contract, and docs validation."
  - "Given sprint docs are no longer a live planning shape, when authors follow the current planning docs, then `REF-sprint-planning-workflow`, the sprint template, `docs/index.md`, and `.codex/handoff.md` treat sprint docs as deprecated historical archive and direct planning through epic/story/PR + target-based review docs."
  - "Given the active backlog already uses dedicated follow-up review records, when this backfill story is read, then it records the shipped split of current review gates into `REV-PR-*` docs and the governing role of `REF-review-workflow` for future migrations."
---

## Context

The repo already landed a meaningful docs-as-code tightening pass without a dedicated planning lane
to own it. That pass established the current target-based review model, clarified that sprint docs
are legacy archive rather than a live planning surface, and aligned the governing reference, rule,
template, docs contract, validator, index, and handoff around that shape.

This story backfills those already-shipped changes so the backlog explains how the current
docs-as-code system was created.

## Notes

- This is a backfill story for already-implemented docs changes; it should not be reopened to
  justify unrelated product work.
- The remaining historical review migration is intentionally split into `ST-34-02` so the shipped
  baseline stays distinct from the unfinished archive cleanup lane.

## References

- Epic parent: [EPIC-34](../epics/epic-34-docs-as-code-tightening-and-legacy-review-record-migration.md)
- Review workflow reference: [REF-review-workflow](../../reference/ref-review-workflow.md)
- Retired sprint planning workflow: [REF-sprint-planning-workflow](../../reference/ref-sprint-planning-workflow.md)
