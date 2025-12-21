---
type: story
id: ST-11-10
title: "Suggestions flows (contributor + admin review)"
status: ready
owners: "agents"
created: 2025-12-21
epic: "EPIC-11"
acceptance_criteria:
  - "Given a contributor visits /suggestions/new, when submitting a suggestion, then the request is accepted and the user sees confirmation in the SPA"
  - "Given an admin visits /admin/suggestions, when reviewing and deciding on a suggestion, then the decision is persisted and reflected in the SPA"
ui_impact: "Migrates the suggestion workflow for contributors/admins into the SPA."
dependencies: ["ST-11-04", "ST-11-05"]
---

## Context

Suggestions are a core governance flow and must preserve role-based access and auditability.
