---
type: story
id: ST-25-01
title: "Competitive games substrate and Flunk-Out Frenzy bootstrap contract"
status: done
owners: "agents"
created: 2026-03-22
epic: "EPIC-25"
dependencies: ["ADR-0023", "ADR-0073"]
acceptance_criteria:
  - "Given the backend starts, when the curated app registry is listed, then `games.flunk_out_frenzy` is returned with `ui_mode=bespoke_required` and a deterministic curated-app `tool_id`."
  - "Given a signed-in user opens `/apps/games.flunk_out_frenzy`, when the app host resolves the route, then it loads a dedicated `FlunkOutFrenzyView.vue` and does not fall back to the generic `AppDetailView`."
  - "Given the SPA requests `GET /api/v1/apps/games.flunk_out_frenzy/bootstrap`, when the backend responds, then the payload is a typed app-specific bootstrap model containing app metadata, runtime feature flags, and `ruleset_id` without requiring the primary UX to orchestrate generic `start_action` or `tool_sessions` calls."
ui_impact: "Yes (new bespoke app route + bootstrap contract)"
data_impact: "No (registry + API contract only)"
---

## Context

Before gameplay is implemented, Skriptoteket needs the correct curated-app seam
for competitive games: a bespoke route, a typed bootstrap contract, and an app
identity that already reserves future competition fields such as `ruleset_id`.

## Notes

- Register the app through the curated app registry, not through tool editor
  governance.
- Use the existing SPA app host pattern and fail closed if the bespoke view is
  missing.
- Keep the bootstrap contract small and app-level. It should describe the app
  and runtime features, not frame-by-frame play state.
