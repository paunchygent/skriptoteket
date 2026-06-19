---
type: pr
id: PR-0058
title: "Kodredigerare: tool picking, search, and editor menu"
status: done
owners: "agents"
created: 2026-01-26
updated: 2026-06-18
stories:
  - "ST-14-38"
tags: ["frontend", "ux"]
acceptance_criteria:
  - "The Kodredigerare hub (/editor) auto-opens the most recently used tool; /editor?pick=1 is an explicit tool picker."
  - "Search in the hub and in the editor menu is stable (no empty error rows), searches across editable tools, and returns at most 5 matches."
  - "Navigation and labels are consistent: Kodredigerare/Kodredigeraren, Alla verktyg, Visa alla verktyg."
---

## Problem

- Tool picking in the editor was unclear and lacked a cohesive hub.
- Search results in the editor menu could render incorrectly (empty red error row) and hide results.
- Create-tool / modal logic was duplicated across multiple views.

## Goal

- A compact, cohesive Kodredigerare hub to continue where you left off or pick a tool.
- An editor menu to switch/search/create tools that feels like an extension of the editor.
- Stable search UX that always searches tools the user can edit and returns the top 5 matches.

## Non-goals

- A new backend endpoint for “all editable tools” (beyond existing admin/my-tools).
- A new permissions model for tool editing.

## Implementation plan

- Add a `/editor` hub route and `/editor?pick=1` picker view in the SPA.
- Store “recently opened” tools (MRU) per user in localStorage.
- Add an editor-toolbar dropdown “Verktyg” to switch/search/create tools and place it after “Spara/Öppna”.
- Share search logic in a composable and fix the rendering bug where the error row could trigger incorrectly.
- Extract create-draft modal state + submit into a composable for SRP and less duplicated code.

## Test plan

- `pdm run fe-type-check`
- `pdm run fe-lint`
- Playwright (Vite dev): `pdm run ui-editor-smoke --base-url http://127.0.0.1:5173`

## Rollback plan

- Revert the `/editor` route and related UI components (hub + editor menu).
- Fall back to tool navigation via `/my-tools` and `/admin/tools`.

## Closeout Status (as of 2026-06-18)

`PR-0359` repairs this slice to `done`. The current `/editor` hub, MRU reopen,
bounded editable-tool search, and `EditorToolMenu` picker/menu behavior match
the implemented scope described here.
