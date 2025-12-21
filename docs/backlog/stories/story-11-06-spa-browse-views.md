---
type: story
id: ST-11-06
title: "Catalog browse views (professions/categories/tools)"
status: ready
owners: "agents"
created: 2025-12-21
epic: "EPIC-11"
acceptance_criteria:
  - "Given an authenticated user, when visiting /browse, then the SPA lists professions from /api/v1/catalog/professions"
  - "Given a user selects a profession and category, when visiting /browse/:profession/:category, then the SPA lists tools with the same results as the legacy templates"
ui_impact: "Migrates the core browse/catalog experience to the SPA."
dependencies: ["ST-11-04", "ST-11-05"]
---

## Context

Browse flows are the main entry point for users. These must reach parity early to validate the migration approach.
