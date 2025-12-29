---
type: story
id: ST-14-25
title: "UI contract v2.x: layout editor output (layout_editor_v1)"
status: ready
owners: "agents"
created: 2025-12-29
epic: "EPIC-14"
acceptance_criteria:
  - "Given a tool returns a ui_payload output with kind=layout_editor_v1, when normalizing the payload, then the server accepts it (policy-allowed), applies deterministic size limits, and stores it for replay."
  - "Given layout_editor_v1 output exceeds configured caps/budgets, when normalizing, then the output is truncated or dropped deterministically with an actionable system notice (no 500)."
  - "Given an older client or unknown renderer encounters layout_editor_v1, when rendering, then it falls back to an 'unknown output' card without breaking the run view."
  - "Given OpenAPI types are regenerated, then the SPA can type-narrow and render layout_editor_v1 outputs."
dependencies:
  - "ST-10-03"
ui_impact: "Yes (new output renderer kind)"
data_impact: "No (backwards-compatible contract extension)"
---

## Context

The seating-planner “slot + room” workflow requires an interactive UI surface that tools can drive without shipping
arbitrary JavaScript. The platform needs a first-class output kind for a structured, platform-rendered layout editor.

## Goal

Introduce `layout_editor_v1` as a typed output kind in the UI contract, with deterministic normalization and safe size
limits.

## Notes

Reference: `docs/reference/ref-tool-editor-dx-review-2025-12-29.md`
