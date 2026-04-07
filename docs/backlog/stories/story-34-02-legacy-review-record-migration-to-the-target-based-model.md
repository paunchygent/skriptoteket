---
type: story
id: ST-34-02
title: "Legacy review-record migration to the target-based model"
status: done
owners: "agents"
created: 2026-04-06
updated: 2026-04-06
epic: "EPIC-34"
dependencies:
  - "ST-34-01"
  - "REF-review-workflow"
  - "REF-sprint-planning-workflow"
acceptance_criteria:
  - "Given several older review families still reuse the same epic review id across multiple files, when this story is complete, then the touched records are migrated to unique target-based review docs or explicitly preserved as legacy with corrected links and no active ambiguity about which review governs which target."
  - "Given the docs contract and validator now enforce primary-target review semantics, when the migrated review records are validated, then `pdm run docs-validate` passes without review-target drift introduced by the migration."
  - "Given the repo should expose one discoverable planning trail, when this story is complete, then `docs/index.md`, `.agents/handoff.md`, and touched backlog docs point to the migrated target-based review records instead of implying live supplemental epic-ledger reviews or sprint-led planning."
---

## Context

The docs-as-code system now has a canonical retained review model, but several older review
families still reflect the earlier epic-ledger shape. The most obvious current clusters are the
duplicate-id families around `REV-EPIC-08`, `REV-EPIC-14`, and `REV-EPIC-23`.

Until those records are migrated, the repo still carries conflicting signals: the workflow docs,
validator, and current backlog model say one primary target per review doc, while parts of the
historical archive still reuse one epic review id across multiple files.

## Notes

- Preserve retained decision history; migrate with care rather than flattening older docs into a
  false “clean” state.
- When historical splitting would distort the record, prefer explicit legacy framing plus corrected
  links over a misleading rewrite.

## Planned PR slices

- [PR-0230: ST-34-02 legacy review-record migration to the target-based model](../prs/pr-0230-st-34-02-legacy-review-record-migration-to-the-target-based-model.md)

## References

- Epic parent: [EPIC-34](../epics/epic-34-docs-as-code-tightening-and-legacy-review-record-migration.md)
- Review workflow reference: [REF-review-workflow](../../reference/ref-review-workflow.md)
- Retired sprint planning workflow: [REF-sprint-planning-workflow](../../reference/ref-sprint-planning-workflow.md)
