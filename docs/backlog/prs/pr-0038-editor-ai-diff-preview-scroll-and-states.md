---
type: pr
id: PR-0038
title: "Editor AI diff preview: scroll + error/regen states"
status: ready
owners: "agents"
created: 2026-01-17
updated: 2026-01-17
stories:
  - "ST-08-22"
tags: ["frontend", "editor", "ai", "diff", "ux"]
acceptance_criteria:
  - "Given an AI diff preview with fuzz warnings or errors, when the panel content exceeds the viewport, then the diff panel is scrollable and all content is reachable."
  - "Given a successful preview with a large diff, when the user scrolls, then the diff remains usable without clipping action controls or warnings."
  - "Given the proposal is blocked (apply disabled), the user can still scroll the diff preview and reach the Regenerate/Discard actions."
---

## Problem

AI edit-ops preview uses the shared editor workspace panel, but the proposal surface becomes non-scrollable when the diff
is long or when error/fuzz warnings expand the header. In dev repro, the proposal panel is clipped due to the workspace
mode container using `overflow-hidden`, so warnings + diff height exceed the visible area without scroll.

## Goal

Make the AI diff preview panel reliably scrollable across success/error/regenerate states without changing backend
behavior or diff contents.

## Non-goals

- Redesign the diff viewer or change diff rendering logic.
- Modify backend edit-ops, preview, or apply behavior.
- Introduce new AI/LLM workflow changes.

## Implementation plan

1. **Layout fix in workspace panel**
   - Update `frontend/apps/skriptoteket/src/components/editor/EditorWorkspacePanel.vue` so the edit-ops proposal area can
     scroll when it exceeds the available height (remove/relocate `overflow-hidden`, use `min-h-0` + `overflow-y-auto` on
     the proposal wrapper).
2. **Edit-ops panel sizing**
   - Update `frontend/apps/skriptoteket/src/components/editor/EditorEditOpsPanel.vue` to use a responsive height clamp
     for the diff viewer (e.g. `clamp(240px, 40vh, 360px)`) so larger previews use more space without dominating the
     editor column.
   - Keep action buttons and warning blocks readable without clipping.
3. **Regression checks**
   - Ensure source editor mode still scrolls normally and diff mode (version compare) remains unaffected.
   - Validate that error/regen states still render in the proposal header and are visible when scrolling.

## Test plan

- Manual (docker dev stack): open editor, trigger an edit-ops preview with a large diff and confirm the proposal panel
  scrolls (including warning/error states).
- Automation: `pdm run python -m scripts.playwright_st_08_22_edit_ops_diff_scroll_check` (Playwright; requires escalation
  on macOS).

## Rollback plan

Revert the layout changes in `EditorWorkspacePanel.vue` and `EditorEditOpsPanel.vue` to restore prior panel sizing and
overflow behavior.
