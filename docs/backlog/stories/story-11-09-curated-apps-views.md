---
type: story
id: ST-11-09
title: "Curated apps views (`/apps/:app_id`)"
status: ready
owners: "agents"
created: 2025-12-21
epic: "EPIC-11"
acceptance_criteria:
  - "Given an authenticated user visits /apps/:app_id, when the SPA loads, then it renders the curated app run experience with the correct tool UI contract outputs/actions"
  - "Given a curated app run is created, when the user revisits the page, then state and UI payload can be replayed consistently"
ui_impact: "Ensures curated apps remain a first-class surface after the SPA migration."
dependencies: ["ADR-0023", "ADR-0024", "ST-11-04", "ST-11-05"]
---

## Context

Curated apps are part of the product surface and must remain functional under the same SPA and API v1 conventions.
