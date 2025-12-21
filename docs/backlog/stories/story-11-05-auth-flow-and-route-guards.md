---
type: story
id: ST-11-05
title: "Auth flow + route guards"
status: ready
owners: "agents"
created: 2025-12-21
epic: "EPIC-11"
acceptance_criteria:
  - "Given an unauthenticated user visits a protected route, when the SPA loads, then it navigates to /login and preserves the intended destination"
  - "Given a user logs in and receives a session cookie, when navigating to protected routes, then the SPA renders the correct view and role-gated navigation items"
ui_impact: "Replaces server-rendered login/logout pages with SPA equivalents while preserving roles."
dependencies: ["ADR-0009", "ADR-0030"]
---

## Context

The SPA must implement the session + CSRF flow and enforce role guards consistent with backend dependencies.
