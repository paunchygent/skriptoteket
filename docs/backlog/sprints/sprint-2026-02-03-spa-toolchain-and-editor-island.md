---
type: sprint
id: SPR-2026-02-03
title: "Sprint 2026-02-03: SPA toolchain + editor island MVP"
status: done
owners: "agents"
created: 2025-12-19
starts: 2026-02-03
ends: 2026-02-16
objective: "Introduce the Vue/Vite/Tailwind toolchain and ship an editor SPA island MVP for admin/contributor editor surfaces."
prd: "PRD-script-hub-v0.2"
epics: ["EPIC-10"]
stories: ["ST-10-08", "ST-10-09"]
adrs: ["ADR-0025"]
---

## Objective

Set up the approved SPA toolchain and ship the first SPA island where SSR/HTMX complexity is highest: the admin and
contributor tool editors.

## Scope (committed stories)

- ST-10-08: Frontend toolchain for SPA islands (Vue/Vite/Tailwind)
- ST-10-09: Editor SPA island MVP (admin/contributor)

## Out of scope

- Runtime SPA island for end-user interactive tool UI (planned next sprint)
- Site-wide Tailwind migration (explicitly not a goal)

## Risks / edge cases

- Asset integration: ensure Vite manifest integration works in prod and dev.
- CSS collisions: avoid Tailwind/global styles leaking into SSR pages.

## Demo checklist

- Open an admin/contributor editor page and show the SPA island mounts.
- Save a script via API and show success/failure UI states.

## Verification checklist

- `pdm run docs-validate`
- `pdm run test` (or frontend unit tests if added in ST-10-08)
