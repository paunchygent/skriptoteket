---
type: story
id: ST-32-09
title: "Canonical public-route recovery and SPA unmatched state"
status: ready
owners: "agents"
created: 2026-04-07
updated: 2026-04-07
epic: "EPIC-32"
dependencies:
  ["ADR-0028", "ST-11-03", "ST-32-06", "ST-32-07"]
acceptance_criteria:
  - "Given a visitor enters any unmatched SPA URL, when the route resolves, then Skriptoteket renders a visible not-found or recovery surface instead of an empty layout shell."
  - "Given a visitor enters `/public/<app-id>` instead of `/public/apps/<app-id>`, when the route resolves, then the page explains the canonical public curated-app route shape and offers the correct path for `classroom.group-seating-studio`."
  - "Given the canonical route `/public/apps/classroom.group-seating-studio` is used, when this story ships, then the current public Klassrumskartan bootstrap and guest workspace behavior remain unchanged."
ui_impact: "Yes (unmatched-route recovery and malformed public-route guidance surface)"
data_impact: "No"
---

## Context

The backend history fallback is working, but the SPA still fails poorly when the path does not
match a Vue route. For malformed public URLs that means the app shell renders and the route body
goes blank.

This story repairs that failure mode without changing the canonical public route contract.

## Notes

- This is a frontend route-handling story, not a backend history-fallback story.
- The recovery surface should be calm, visible, and teacher-facing rather than dramatic or highly
  technical.
- The canonical public route shape remains `/public/apps/:appId`; this story improves recovery, not
  the route contract itself.
- The follow-up dedicated auth-entry redesign belongs in `ST-32-10` / `PR-0242`, not in this
  route-recovery slice.

## Planned PR slices

- [PR-0240: ST-32-09 SPA catch-all route and malformed public-route recovery](../prs/pr-0240-st-32-09-spa-catch-all-route-and-malformed-public-route-recovery.md)

## References

- Epic parent:
  [EPIC-32](../epics/epic-32-public-curated-app-access-foundation-and-klassrumskartan-demo.md)
- SPA hosting and routing integration:
  [ST-11-03](story-11-03-spa-hosting-fastapi-integration.md)
- Public curated-app baseline:
  [ST-32-06](story-32-06-klassrumskartan-demo-adoption-on-the-public-browser-workspace-profile.md)
