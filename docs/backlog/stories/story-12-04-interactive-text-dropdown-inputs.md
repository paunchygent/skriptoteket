---
type: story
id: ST-12-04
title: "Interactive text/dropdown inputs"
status: blocked
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

## Blocker

This story is **blocked until EPIC-11 is complete (ST-11-13 cutover)** so form UI is implemented once in the SPA (not
duplicated in SSR/HTMX).

