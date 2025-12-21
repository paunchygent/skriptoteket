---
type: story
id: ST-11-08
title: "My runs list + detail"
status: ready
owners: "agents"
created: 2025-12-21
epic: "EPIC-11"
acceptance_criteria:
  - "Given an authenticated user, when visiting /my-runs, then the SPA lists the user's runs via /api/v1/my-runs"
  - "Given a run id, when visiting /my-runs/:id, then the SPA renders run detail and allows navigation back to results and artifacts"
ui_impact: "Replaces server-rendered run history pages with SPA equivalents."
dependencies: ["ST-11-04", "ST-11-05", "ST-11-07"]
---

## Context

Users need a reliable history to revisit outputs and artifacts; this also validates pagination and authorization rules.
