---
type: story
id: ST-12-03
title: "Personalized tool settings"
status: done
owners: "agents"
created: 2025-12-21
epic: "EPIC-12"
acceptance_criteria:
  - "Given a tool declares user-configurable settings, when a user saves settings, then the settings persist for that user and are applied on future runs"
  - "Given a user updates settings, when the next run starts, then the runner receives the effective settings without exposing other users’ settings"
ui_impact: "Adds per-user preferences to tool run flows (e.g., defaults, templates, output options)."
data_impact: "Introduces per-user persisted settings keyed by tool and settings schema version."
dependencies: ["ST-11-13"]
---

## Context

Many tools benefit from stable per-user defaults (e.g., preferred output format, organization name, recurring values)
without requiring the user to re-enter them on every run.

## Status

This story was blocked until EPIC-11 cutover (ST-11-13). EPIC-11 is complete as of **2025-12-23**; implement settings UX
directly in the SPA (no SSR duplication).

Implemented end-to-end on **2025-12-24**.
