---
type: story
id: ST-11-03
title: "Serve SPA from FastAPI (manifest + history fallback)"
status: ready
owners: "agents"
created: 2025-12-21
epic: "EPIC-11"
acceptance_criteria:
  - "Given a production SPA build exists, when the FastAPI app runs, then deep links (e.g. /browse/foo) serve the SPA index and load hashed assets successfully"
  - "Given API routes exist under /api, when requesting /api/*, then the SPA history fallback does not intercept API responses"
ui_impact: "Enables the SPA to own all route paths without redirects."
dependencies: ["ADR-0027", "ADR-0028"]
---

## Context

The SPA must work with history routing and be served as a first-class part of the FastAPI app.
