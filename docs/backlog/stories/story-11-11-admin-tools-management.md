---
type: story
id: ST-11-11
title: "Admin tools list + publish/depublish"
status: ready
owners: "agents"
created: 2025-12-21
epic: "EPIC-11"
acceptance_criteria:
  - "Given an admin visits /admin/tools, when the SPA loads, then it lists tools and shows publish state via /api/v1/admin/tools"
  - "Given an admin publishes or depublishes a tool, when the action completes, then the SPA reflects the updated state and shows a toast message"
ui_impact: "Moves admin tool management to the SPA and validates CSRF + role enforcement."
dependencies: ["ST-11-04", "ST-11-05"]
---

## Context

Admin tools management is a daily operational surface and must be stable before cutover.
