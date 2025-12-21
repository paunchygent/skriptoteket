---
type: story
id: ST-11-07
title: "Tool run + results (uploads, artifacts, typed outputs)"
status: ready
owners: "agents"
created: 2025-12-21
epic: "EPIC-11"
acceptance_criteria:
  - "Given an authenticated user visits /tools/:slug/run, when uploading a file and submitting, then the tool executes and the SPA navigates to a run result view"
  - "Given a run has artifacts and typed ui_payload outputs, when viewing results, then the SPA renders outputs and allows artifact downloads"
ui_impact: "Moves the main tool execution flow into the SPA and reuses the typed UI contract components."
dependencies: ["ADR-0022", "ADR-0024", "ST-11-04", "ST-11-05"]
---

## Context

Tool execution and results are the highest-value user flow and must work reliably with multipart uploads and artifact
downloads.
