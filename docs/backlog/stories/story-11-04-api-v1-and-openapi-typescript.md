---
type: story
id: ST-11-04
title: "API v1 conventions + OpenAPI → TypeScript generation"
status: ready
owners: "agents"
created: 2025-12-21
epic: "EPIC-11"
acceptance_criteria:
  - "Given /api/v1 endpoints are implemented, when inspecting the OpenAPI schema, then request/response models are documented and stable under /api/v1"
  - "Given a developer runs the type generation command, when the SPA is built, then it imports the generated types without hand-written API DTO drift"
ui_impact: "Stabilizes SPA/backend contracts and prevents schema drift."
dependencies: ["ADR-0030"]
---

## Context

We want the backend OpenAPI schema to be the source of truth for all SPA DTOs, validated in CI.
