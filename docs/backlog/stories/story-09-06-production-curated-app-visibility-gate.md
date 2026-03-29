---
type: story
id: ST-09-06
title: "Production curated-app visibility gate"
status: done
owners: "agents"
created: 2026-03-30
updated: 2026-03-30
epic: "EPIC-09"
dependencies: ["ADR-0023", "ST-10-05", "ST-25-01"]
acceptance_criteria:
  - "Given Skriptoteket starts with `ENVIRONMENT=production`, when the curated app registry is listed, then only production-approved curated apps are returned and `demo.counter` plus `games.flunk_out_frenzy` are absent."
  - "Given a signed-in user or SPA deep link requests a curated app hidden by the production gate, when the backend resolves the app registry entry, then the request fails closed with `not_found` rather than exposing app metadata or bootstrap payloads."
  - "Given a production user has legacy favorites or recent-run records pointing at a hidden curated app, when those surfaces are listed, then the hidden app is omitted."
  - "Given Skriptoteket starts in non-production environments, when the curated app registry is listed, then local/dev testing still exposes the demo and in-development curated apps."
ui_impact: "No direct UI redesign; production catalog/app-host surfaces inherit backend gating."
data_impact: "No schema change; existing favorite/recent data must tolerate hidden registry entries."
---

## Context

Skriptoteket is about to expose Klassrumskartan to real colleague testing in the
deployed production environment. That makes registry hygiene a production
hardening concern: demo apps and in-development curated apps must not remain
discoverable simply because they are valid local/dev test surfaces.

Today the in-memory curated app registry publishes all known curated apps in all
environments. That means the production catalog, app-detail lookup, and
app-specific routes can expose demo or unfinished curated apps unless we add an
explicit production-only visibility gate.

## Notes

- Implement the gate in backend registry/config code, not as a frontend-only
  hide.
- The first blocked production app ids are:
  - `demo.counter`
  - `games.flunk_out_frenzy`
- Prefer an explicit production allowlist so new curated apps do not become
  production-visible by accident.
- Keep the change local to curated app discoverability/access. Do not remove
  local/dev support for these apps.
