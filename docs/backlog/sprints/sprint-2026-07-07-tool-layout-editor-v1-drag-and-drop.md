---
type: sprint
id: SPR-2026-07-07
title: "Sprint 2026-07-07: Tool layout editor v1 (drag/drop)"
status: planned
owners: "agents"
created: 2025-12-29
starts: 2026-07-07
ends: 2026-07-20
objective: "Add drag/drop interactions to the layout editor v1 using a proven library, keeping keyboard-first flows intact."
prd: "PRD-script-hub-v0.2"
epics: ["EPIC-14"]
stories: ["ST-14-27", "ST-14-28"]
adrs: ["ADR-0047"]
---

## Objective

Make the layout editor feel like a true seating planner by adding drag/drop for students between slots, while retaining
accessible click/keyboard assignment for users who prefer it (or on devices where drag/drop is awkward).

Reference context: `docs/reference/ref-tool-editor-dx-review-2025-12-29.md`

## Scope (committed stories)

- [ST-14-27: Layout editor v1: drag/drop interactions (library-based)](../stories/story-14-27-layout-editor-v1-drag-drop.md)
- [ST-14-28: Layout editor v1: UX polish + accessibility + tests](../stories/story-14-28-layout-editor-v1-ux-polish-and-a11y.md)

## Out of scope

- Advanced geometry editing (resize/rotate desk groups).
- Multi-room / multi-floor buildings.
- Real-time collaboration (multi-user live editing).

## Decisions required (ADRs)

- Confirm the drag/drop library choice and constraints (bundle size, accessibility posture, mobile support).
  - Note: ADR-0047 defines the baseline editor model; this sprint chooses the DnD library.

## Risks / edge cases

- Accessibility: drag/drop must not become the only way to edit.
- Mobile/touch support: ensure touch-friendly drag handles or keep click-to-assign as primary on mobile.
- Performance: avoid excessive re-rendering with larger class sizes.

## Execution plan (suggested)

1) Add a well-known drag/drop library (e.g. `interactjs`) and implement:
   - drag student “chips” into slots
   - swap/move between slots
   - visual drop targets + invalid drop feedback
2) Keep “apply changes” semantics (batch updates) rather than invoking a tool run on every drag.
3) Add basic component tests for keyboard assignment + a couple of drag/drop scenarios.

## Demo checklist

- Drag a student into an empty slot.
- Swap students between two occupied slots.
- Use keyboard/click assignment to perform the same operations without drag/drop.

## Verification checklist

- `pdm run docs-validate`
- `pdm run lint`
- `pdm run test`
- Live functional check (backend + SPA dev); record steps in `.agent/handoff.md`.
