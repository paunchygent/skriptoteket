---
type: story
id: ST-14-23
title: "UI contract v2.x: action defaults / prefill"
status: done
owners: "agents"
created: 2025-12-29
updated: 2026-01-15
epic: "EPIC-14"
links: ["ADR-0060"]
acceptance_criteria:
  - "Given a tool returns next_actions with field defaults/prefill metadata, when the UI renders the action form, then matching fields are prefilled with those values."
  - "Given a default is invalid for the field schema/type, when normalizing ui_payload, then the server deterministically rejects or strips the invalid default and surfaces an actionable error (no undefined behavior)."
  - "Given a tool does not provide defaults/prefill metadata, when rendering action forms, then behavior remains unchanged."
  - "Given ui_payload is stored and later replayed, when rendering a historical run, then the prefill metadata is preserved and does not break rendering."
dependencies:
  - "ST-14-03"
ui_impact: "Yes (runtime + editor sandbox action forms)"
data_impact: "No (backwards-compatible payload extension)"
---

## Context

Today, “prefilled action fields” can only be approximated with client-side stickiness (remember last submitted values).
That improves DX but is not a real platform feature: tools can’t intentionally guide users by providing defaults based on
state or prior outputs.

## Goal

Extend the typed UI contract (v2.x) so tools can provide **explicit defaults/prefill** for action input fields in a
backwards-compatible way.

## Notes

Reference: `docs/reference/ref-tool-editor-dx-review-2025-12-29.md`
