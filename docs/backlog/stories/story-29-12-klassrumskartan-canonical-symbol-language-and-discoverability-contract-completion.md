---
type: story
id: ST-29-12
title: "Klassrumskartan — Canonical symbol language and discoverability contract completion"
status: ready
owners: "agents"
created: 2026-04-01
epic: "EPIC-29"
dependencies:
  - "ST-29-01"
  - "ST-29-11"
acceptance_criteria:
  - "Given repeated operations render across planner, editor, and adjacent tool-grade SPA surfaces, when this story ships, then undo, redo, history, configure context, create, close, export/download, zoom, fit view, and overflow use one canonical symbol-and-label language without unicode or surface-local alternates."
  - "Given icon-only and icon-led controls remain part of the dense-control system, when this story is complete, then accessible names, visible labels, hover aids, and nearby discoverability cues follow one documented contract across the shared control family."
  - "Given configure-context destinations differ by surface such as `Regler` or `Inställningar`, when the final symbol language is applied, then those controls are disambiguated through the canonical label/icon contract rather than collapsing to ambiguous bare icons."
  - "Given the repo still relies mainly on browser-native `title` discoverability, when this story defines the symbol/language baseline, then `ST-29-08` can later upgrade that baseline into a custom tooltip system without reopening the canonical operation vocabulary."
ui_impact: "Yes (shared canonical symbols, labels, and discoverability rules)"
data_impact: "No"
---

## Context

The first shared dense-tool primitive pass shipped enough canonical symbol work to support the
current planner. What remains is the broader completion pass that turns those assets into one
stable site/app-wide language instead of a planner-led foundation with some remaining drift.

This story isolates the symbol, labeling, and discoverability completion work from the already
shipped workspace layout stories.

## Notes

- This is a follow-on definition and audit story, not a new workspace redesign.
- The first implementation goal is to finish the operation vocabulary itself. The later custom
  tooltip system remains a separate enhancement story under `ST-29-08`.
- The story should cover both accessibility truthfulness and teacher-facing discoverability, not
  just icon swaps in isolation.

## References

- Epic parent: [EPIC-29](../epics/epic-29-klassrumskartan-desktop-first-workspace-overhaul.md)
- Primitive foundation: [ST-29-01](story-29-01-klassrumskartan-canonical-operation-symbols-and-planner-control-primitives.md)
- Primitive tightening prerequisite: [ST-29-11](story-29-11-klassrumskartan-shared-site-and-app-dense-control-primitive-tightening.md)
- Tooltip enhancement follow-on: [ST-29-08](story-29-08-klassrumskartan-shared-custom-tooltip-system-and-global-hover-contract.md)
- Shared control matrix: [REF-shared-tool-control-language-v1](../../reference/ref-shared-tool-control-language-v1.md)
