---
type: story
id: ST-12-03
title: "Personalized tool settings"
status: blocked
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

## Blocker

This story is **blocked until EPIC-11 is complete (ST-11-13 cutover)** so settings UX is implemented once in the SPA
(not duplicated in SSR/HTMX).
