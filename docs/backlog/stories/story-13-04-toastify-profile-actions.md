---
type: story
id: ST-13-04
title: "Toastify profile actions"
status: ready
owners: "agents"
created: 2025-12-25
epic: "EPIC-13"
acceptance_criteria:
  - "Given a user updates their profile, when the save succeeds, then the app shows a success toast and does not render a layout-shifting inline success banner"
  - "Given a user updates their email, when the save succeeds, then the app shows a success toast and does not render a layout-shifting inline success banner"
  - "Given a user updates their password, when the save succeeds, then the app shows a success toast and does not render a layout-shifting inline success banner"
  - "Validation errors remain inline as system messages (not toasts)"
ui_impact: "Removes layout-shifting inline success banners from ProfileView and replaces them with the shared toast overlay."
data_impact: "None."
dependencies: ["ST-13-01", "ADR-0037"]
---

## Context

EPIC-13 introduced a shared toast system for transient action feedback (ADR-0037). Most key flows have been migrated
(ST-13-02), but `ProfileView` still uses inline success banners which cause layout shift.

## Scope

- Replace ProfileView inline success banners with `useToast()` success toasts:
  - profile update
  - email update
  - password update
- Keep validation + blocking errors inline (system messages).

## Migration targets

- `frontend/apps/skriptoteket/src/views/ProfileView.vue`
