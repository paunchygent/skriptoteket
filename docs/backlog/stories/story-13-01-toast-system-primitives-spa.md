---
type: story
id: ST-13-01
title: "Toast system primitives (SPA)"
status: done
owners: "agents"
created: 2025-12-25
epic: "EPIC-13"
acceptance_criteria:
  - "Given a user completes a successful action, when the app triggers a toast, then an overlay toast appears without layout shift and auto-dismisses"
  - "Given an action fails in a non-blocking way, when the app triggers a failure toast, then the toast uses burgundy styling and is announced accessibly"
  - "Given an action triggers a warning, when the app triggers a warning toast, then the toast uses amber styling and is announced accessibly"
  - "Given multiple toasts are triggered quickly, when they render, then they stack (bounded) and remain readable on mobile"
  - "Toast styling is implemented as shared primitives in frontend/apps/skriptoteket/src/assets/main.css (no ad-hoc inline styling)"
  - "REF-toast-system-messages documents toast API, variants, and when to use inline system messages"
ui_impact: "Replaces per-view inline success/error blocks for transient feedback with a global animated overlay."
data_impact: "None."
dependencies: ["ADR-0037"]
---

## Context

The SPA currently uses inline `successMessage`/`errorMessage` blocks across views and composables. This creates
layout shifts and inconsistent styling/behavior.

This story introduces the core toast system primitives (store/composable + host + CSS primitives) that other stories
can adopt incrementally.

## Notes

- Toast variants: info (navy), success (pine green), warning (amber), failure (burgundy).
- Validation and blocking errors remain inline (sticky, close-only), per ADR-0037.
