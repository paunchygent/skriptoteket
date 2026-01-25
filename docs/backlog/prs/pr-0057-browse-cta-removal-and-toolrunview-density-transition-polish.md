---
type: pr
id: PR-0057
title: "UI cohesion: remove browse CTAs + ToolRunView density and transition polish"
status: in_progress
owners: "agents"
created: 2026-01-25
updated: 2026-01-25
stories:
  - "ST-16-05"
  - "ST-11-07"
tags: ["frontend"]
acceptance_criteria:
  - "Browse lists/cards do not render per-item 'Välj' CTA buttons; item selection is done by clicking the row/card itself."
  - "Browse hover/active styling uses the dashboard-aligned behavior: transform + brutal shadow escalation, plus hue change (no competing arrow treatment on bookmarked cards)."
  - "ToolRunView renders nested results/actions/artifacts using embedded density (no shadow-in-shadow) and matches the editor’s compact/inset panel hierarchy."
  - "ToolRunView show/hide regions (settings, step indicator, errors, running state, results) animate height/opacity to remove jumpiness; respects prefers-reduced-motion."
  - "All changes preserve keyboard navigation, focus-visible outlines, and correct link/button semantics (including bookmark toggles)."
---

## Problem

1) **Browse UI drift**: browse surfaces currently mix “row navigation” and a per-item CTA button (“Välj”) that uses the
same brutal button primitives as true CTAs. This dilutes the CTA hierarchy (buttons with brutal shadow should be
reserved for high-intent actions like “Logga in”).

2) **Hover alignment**: browse cards should align with the dashboard interaction language (transform + brutal shadow
escalation). On browse cards with bookmarks, we must avoid adding an arrow/CTA treatment that competes with the
bookmark icon.

3) **ToolRunView jumpiness + nested shadows**: ToolRunView currently introduces nested cards (shadow-in-shadow) for
outputs/actions/artifacts, and show/hide regions snap open/closed without a cohesive transition approach.

## Goal

- Remove per-item “Välj” CTAs from browse views and make the row/card itself the interaction target.
- Align hover behavior with the dashboard (transform + brutal shadow escalation) and use hue change (navy → burgundy)
  as the primary hover signal on bookmarked cards.
- Make ToolRunView feel as polished as the tool editor:
  - embedded density for nested sections
  - consistent inset panel hierarchy
  - smooth height/opacity transitions for dynamic regions

## Non-goals

- Changing catalog API behavior or filters.
- Redesigning the browse layout structure beyond removing the CTA + adjusting hover.
- Changing tool run domain behavior (polling, actions, artifacts).

## Decisions (LOCKED)

- **No browse per-item CTA buttons**: remove “Välj” buttons from browse lists/cards (keep bookmark toggle).
- **Dashboard-aligned hover**: transform + brutal shadow escalation; add hue change on title/label.
- **No arrow competition** on bookmarked cards: do not introduce a right-arrow hover treatment on cards that have the
  bookmark icon (browse cards).
- **ToolRunView embedded density**: the tool card is the “outer panel”; nested panels should avoid their own shadows.
- **Transitions**: use height + opacity transitions for dynamic regions, respecting prefers-reduced-motion.

## Implementation plan

### 1) BrowseToolsView: remove “Välj” CTA and make rows clickable

File: `frontend/apps/skriptoteket/src/views/BrowseToolsView.vue`

- Replace the per-item `RouterLink.btn-ghost` (“Välj”) with a single `RouterLink` that wraps the whole row, matching
  the established browse list pattern used by:
  - `BrowseProfessionsView.vue`
  - `BrowseCategoriesView.vue`
- Keep the list semantics (`ul/li`) but make the row itself the link target.
- Ensure:
  - summary text truncation still works
  - mobile tap targets are full-row
  - focus-visible outline uses the existing token outline pattern

### 2) CatalogItemCard: remove the list-variant CTA and make list cards interactive

File: `frontend/apps/skriptoteket/src/components/catalog/CatalogItemCard.vue`

- Remove the list-variant action `RouterLink` (“Välj/Öppna”) and make list cards clickable the same way compact cards
  already are (card click + keyboard Enter/Space → navigate).
- Keep bookmark toggle as the only separate control; it must:
  - remain a `button`
  - stop propagation so it doesn’t trigger navigation
  - keep its focus-visible outline
- Add dashboard-aligned hover for list cards:
  - `transform: translate(-2px, -2px)`
  - `box-shadow` escalates to the brutal token (matching dashboard)
  - hue change on title/primary label (navy → burgundy) instead of arrow animations

### 3) BrowseFlatView: rely on card interactivity (no CTA)

File: `frontend/apps/skriptoteket/src/views/BrowseFlatView.vue`

- No structural changes beyond ensuring the list uses the interactive cards without rendering CTAs.

### 4) ToolRunView: embedded density for nested sections

File: `frontend/apps/skriptoteket/src/views/ToolRunView.vue`

- Pass embedded/compact density into nested components so they render inset panels rather than separate shadowed cards:
  - `ToolInputForm` → `density="compact"`
  - `ToolFileFieldPicker` → `density="compact"`
  - `ToolRunControlBar` → `density="compact"`
  - `UiOutputRenderer` → `density="compact"`
  - `ToolRunActions` → `density="compact"`
  - `ToolRunArtifacts` → `density="compact"`
  - `SessionFilesPanel` → `density="compact"` (inside the tool card)
  - `ToolRunSettingsPanel` → `variant="embedded"` + `density="compact"`

### 5) ToolRunView: cohesive show/hide transitions (anti-jank)

New component: `frontend/apps/skriptoteket/src/components/ui/UiCollapse.vue`

- Provide a reusable height+opacity transition (same mechanics as `UsageInstructions.vue`) with:
  - `prefers-reduced-motion` support
  - no layout-thrashing (measure scrollHeight once per open/close)
- Apply `UiCollapse` to ToolRunView sections that currently snap:
  - settings panel region
  - step indicator region
  - error banner region
  - running state region
  - results region (enter/leave)

### 6) Playwright runtime smoke: remove dependency on “Välj” link

File: `scripts/playwright_ui_runtime_smoke.py`

- Replace the three browse navigations that click `link[name=/Välj/i]` with a stable selector that clicks the row/card:
  - Use the tool title as the primary target (e.g. click the row link containing `Demo: Interaktiv`).
  - Do **not** rely on the removed CTA label.

## Test plan

Per your instruction: **skip testing until the PR is approved and implemented**.

After implementation (later):
- Frontend: `pdm run fe-lint`, `pdm run fe-test`
- Manual: verify browse (no CTAs), hover behavior, and ToolRunView transitions on mobile + desktop.

## Rollback plan

- Revert the PR-0057 commit(s).
- Restore per-item browse CTAs and ToolRunView default density without transitions.
