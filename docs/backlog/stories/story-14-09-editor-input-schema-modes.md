---
type: story
id: ST-14-09
title: "Editor: input_schema modes (remove null vs [] footgun)"
status: ready
owners: "agents"
created: 2025-12-29
epic: "EPIC-14"
acceptance_criteria:
  - "Given a tool author edits a draft tool, when configuring pre-run inputs, then the editor provides an explicit mode selector (Legacy upload-first vs Schema-driven vs No inputs)."
  - "Given Legacy upload-first is selected, when saving the draft, then the stored input_schema remains null and the UX communicates that files are required to run."
  - "Given Schema-driven is selected with no fields, when saving the draft, then the stored input_schema is an empty array [] and the UX communicates that files are optional unless a file field exists."
  - "Given an existing tool version has input_schema=null, when opening the editor, then the mode selector defaults to Legacy upload-first without changing stored data until the author explicitly edits/saves."
dependencies:
  - "ADR-0027"
  - "ST-14-04"
ui_impact: "Yes (tool editor schema panel)"
data_impact: "No (representation already supported; this story is about explicit UX)"
---

## Context

Today, the difference between `input_schema: null` and `input_schema: []` changes runtime behavior, but the editor UI
makes it easy to accidentally produce `null` (empty textarea), creating surprising “files required” behavior.

## Goal

Make input behavior explicit, predictable, and hard to accidentally change.

## Notes

Reference: `docs/reference/ref-tool-editor-dx-review-2025-12-29.md`
