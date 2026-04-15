---
type: reference
id: REF-frontend-transition-continuity-v1
title: "Frontend transition continuity pattern and adoption inventory v1"
status: active
owners: "agents"
created: 2026-03-29
updated: 2026-03-29
topic: "frontend-transition-continuity"
links:
  [
    "ADR-0077",
    "EPIC-30",
    "ST-30-01",
    "PR-0165",
    "EPIC-29",
    "ST-29-02",
    "REF-frontend-design-system-codemap-2026-03-28",
    "REF-klassrumskartan-workspace-ui-doctrine-2026-03-28",
    "REF-tool-editor-framework-codemap",
  ]
---

## Purpose

This note turns the recent Klassrumskartan shell-transition fix into a reusable frontend standard.

Use it when a Skriptoteket surface:

- keeps one visible shell/frame
- switches between mutually exclusive work areas through a selector, rail, or mode toggle
- needs the switch to feel seamless rather than visibly re-mounted

## Canonical continuity pattern

The only approved default for qualifying same-shell transitions is:

1. Keep the current shell and outgoing surface visible.
2. Prepare the incoming surface first.
3. Freeze shell copy if upstream state would otherwise fall back during the handoff.
4. Crossfade the two surfaces with a short overlap.
5. Remove the outgoing surface only after the incoming one is mounted and visible.

## Required implementation rules

- Preserve one stable shell for title, selector, status, and other shared framing UI.
- Prefer opacity-only crossfades for the actual handoff.
- Keep the leaving surface absolutely stacked during fade-out to avoid a blank gap.
- Delay the transition if the incoming surface is not ready; do not clear the UI just to start the
  animation sooner.
- If local secondary surfaces would flash stale content during the handoff, hide or localize them
  while the shell remains stable.
- Keep transition labels local and compact; never replace the whole workspace with a loading void.

## Disallowed patterns

- `fade out -> blank gap -> fade in`
- `mode="out-in"` on qualifying same-shell workspace swaps
- dropping shell labels/status to generic fallback state during the handoff
- tearing down the old workspace before the new one is mounted
- replacing continuity with a spinner-only empty interstitial

## Current proving reference

The canonical proving reference is the planner workspace shell fix:

- `frontend/apps/skriptoteket/src/views/apps/ClassroomPlannerView.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerWorkspaceShell.vue`
- `frontend/apps/skriptoteket/src/views/apps/classroomPlannerRouteShellWorkspace.ts`

That implementation keeps the planner shell rendered, snapshots top-panel state during handoff,
and uses an overlap crossfade instead of an `out-in` swap.

## Adoption inventory

| Surface | Selector / switch | Current files | Current status | Priority | Notes |
|--------|-------------------|---------------|----------------|----------|-------|
| Klassrumskartan workspace shell | `Översikt` / `Grupper` / `Sittplatser` / `Regler` | `ClassroomPlannerView.vue`, `PlannerWorkspaceShell.vue`, `classroomPlannerRouteShellWorkspace.ts` | Baseline shipped locally | Reference | This is the canonical implementation to copy. |
| Script editor workspace shell | `Kod` / `Metadata` / `Test` / `Diff` | `EditorWorkspacePanel.vue`, `ScriptEditorPageShell.vue`, `useScriptEditorPageState.ts` | Not yet adopted | P1 | Strongest next target: one stable shell already exists, but the main panel swap still lacks the continuity contract. |
| Rules local map surface | `Planeringskarta` / `Sittschema` | `PlannerRulesMapCanvas.vue` | Candidate | P2 | Same toolbar and zoom shell persist while the map projection swaps. |
| Tool-run file picker field surface | `Ladda upp` / `Välj sparade` | `ToolFileFieldPicker.vue` | Candidate | P2 | A smaller same-card shell; transition should preserve the field frame and avoid abrupt body swaps. |
| Vault panel list surface | `Aktiva` / `Papperskorg`, plus sort subrail | `VaultPanel.vue` | Candidate | P3 | Lower risk than editor/planner, but still a selector-driven persistent shell. |

## Adjacent `out-in` audit queue

These current `out-in` usages are worth auditing, but they are not the first `ADR-0077` adoption
targets because they are not the main selector-driven dense-workspace shells:

- `frontend/apps/skriptoteket/src/App.vue`
- `frontend/apps/skriptoteket/src/components/layout/AuthTopBar.vue`
- `frontend/apps/skriptoteket/src/components/profile/ProfileInlineField.vue`
- `frontend/apps/skriptoteket/src/views/ProfileView.vue`

## Recommended rollout order

1. Code editor workspace selector
2. Planner local selector surfaces (`Regler` map view and any remaining same-shell subrails)
3. Tool-run file picker and Vault panel continuity passes
4. Separate audit of adjacent `out-in` usages outside the main dense-workspace selector scope

## Verification expectations

For any implementation slice under this pattern:

- add focused component coverage for the affected shell/surface handoff
- verify there is no blank frame between outgoing and incoming surfaces
- verify shell labels/status do not flash to fallback copy
- run a live browser proof on `http://127.0.0.1:5173` when UI behavior changes
- record the proof in `.codex/handoff.md`
