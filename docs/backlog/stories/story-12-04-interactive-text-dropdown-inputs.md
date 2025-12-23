---
type: story
id: ST-12-04
title: "Interactive text/dropdown inputs"
status: ready
owners: "agents"
created: 2025-12-21
epic: "EPIC-12"
acceptance_criteria:
  - "Given a tool defines a simple input form (text + dropdown), when a user opens the run view, then the SPA renders the form and submits values as part of the run"
  - "Given inputs are invalid, when submitting, then the user sees a clear validation error and the runner is not invoked"
ui_impact: "Reduces friction by allowing common “small inputs” without requiring file uploads."
data_impact: "Adds structured input values to ToolRun audit/debug metadata (no raw files)."
dependencies: ["ST-11-13"]
---

## Context

Many tools need only a few parameters (text, dropdowns) rather than a file upload. Supporting this expands tool
usability and reduces “upload a dummy file” workarounds.

## Status

This story was blocked until EPIC-11 cutover (ST-11-13). EPIC-11 is complete as of **2025-12-23**; implement form UI
directly in the SPA (no SSR duplication).
