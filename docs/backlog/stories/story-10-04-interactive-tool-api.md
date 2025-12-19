---
type: story
id: ST-10-04
title: "Interactive tool API endpoints (start_action + read APIs)"
status: ready
owners: "agents"
created: 2025-12-19
epic: "EPIC-10"
acceptance_criteria:
  - "Given a user invokes start_action with expected_state_rev, when execution completes, then the response includes run_id and the updated session state_rev"
  - "Given a run exists, when get_run is called, then the API returns stored ui_payload, status, and artifacts metadata"
  - "Given a run has artifacts, when list_artifacts is called, then the API returns download URLs for stored artifacts"
ui_impact: "Enables an embedded editor SPA and richer end-user tool UI without relying on HTMX partials."
dependencies: ["ADR-0024", "ST-10-02", "ST-10-03"]
---

## Context

Interactive tools require a minimal API surface that supports turn-taking and state persistence while remaining
compatible with the existing server-rendered UI.

