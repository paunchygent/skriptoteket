---
type: story
id: ST-14-09
title: "Editor: remove legacy input_schema=null (always schema-driven inputs)"
status: done
owners: "agents"
created: 2025-12-29
updated: 2026-01-02
epic: "EPIC-14"
acceptance_criteria:
  - "Given a tool author edits a draft tool, when configuring pre-run inputs, then the editor only offers schema-driven options (no legacy upload-first mode)."
  - "Given a tool has no pre-run inputs, when saving the draft, then the stored input_schema is an empty array ([])."
  - "Given a tool requires files before run, when saving the draft, then input_schema includes a file field with min=1 and max=UPLOAD_MAX_FILES."
  - "Given a tool accepts optional files before run, when saving the draft, then input_schema includes a file field with min=0 and max=UPLOAD_MAX_FILES."
  - "Given an existing tool version has input_schema=null, when migrating, then it is converted to a schema-driven file field representation preserving current behavior (files required)."
dependencies:
  - "ADR-0027"
  - "ST-14-04"
ui_impact: "Yes (tool editor schema panel)"
data_impact: "Yes (migrate tool versions away from input_schema=null)"
---

## Context

Before ST-14-09, the difference between `input_schema: null` and `input_schema: []` changed runtime behavior, but the
editor UI made it easy to accidentally produce `null` (empty textarea), creating surprising “files required” behavior.

## Goal

Make input behavior explicit, predictable, and hard to accidentally change.

In the current product phase (advanced prototype; no user-generated tools in production), we can remove the legacy
`input_schema=null` mode entirely and represent the file picker as schema (`kind: "file"`), making schema-driven inputs
the only supported authoring path.

## Notes

Reference: `docs/reference/ref-tool-editor-dx-review-2025-12-29.md`
