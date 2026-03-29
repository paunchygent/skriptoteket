---
type: epic
id: EPIC-30
title: "Frontend transition continuity for same-shell selectors"
status: proposed
owners: "agents"
created: 2026-03-29
outcome: "Teachers and authors experience selector-driven same-shell transitions as seamless continuity instead of blank fades or shell jump cuts across planner, editor, and other dense SPA workspaces."
dependencies:
  [
    "ADR-0027",
    "ADR-0029",
    "ADR-0037",
    "ADR-0077",
    "EPIC-29",
    "REF-frontend-transition-continuity-v1",
    "REF-frontend-design-system-codemap-2026-03-28",
    "REF-tool-editor-framework-codemap",
  ]
---

## Scope

- Establish one repo-wide same-shell transition continuity standard for selector-driven SPA
  workspaces.
- Inventory all current dense-workspace selector or rail transitions that should adopt the
  continuity pattern.
- Prioritize the adoption order, starting with the code editor and then smaller selector-driven
  surfaces.
- Convert the recent Klassrumskartan fix from local implementation knowledge into reusable
  frontend doctrine and backlog ownership.

## Out of Scope

- Route-to-route page transition redesign as a whole.
- Modal, popover, or drawer motion that does not represent a same-shell workspace handoff.
- General animation polish unrelated to continuity failures.
- Domain, backend, or API changes.

## Risks

- If this remains planner-only knowledge, other dense shells will reintroduce blank interstitials
  or jump-cut fallback copy.
- If the editor adopts a different transition model, Skriptoteket will develop two competing
  same-shell motion languages.
- If inventory and adoption are not separated, smaller selector swaps may steal attention before
  the higher-value editor shell is fixed.

## Story Stack

- [ST-30-01: Frontend transition continuity inventory and canonical adoption plan](../stories/story-30-01-frontend-transition-continuity-inventory-and-canonical-adoption-plan.md)

## Notes

- `EPIC-30` is intentionally cross-app. It exists so the planner fix becomes a shared standard
  rather than a local exception inside `EPIC-29`.
- The first implementation target after review is the code editor workspace selector.
- Additional adoption stories should be split out after `ST-30-01` is reviewed and the inventory is
  accepted.
- This epic requires review approval before implementation begins per the repo review workflow.
