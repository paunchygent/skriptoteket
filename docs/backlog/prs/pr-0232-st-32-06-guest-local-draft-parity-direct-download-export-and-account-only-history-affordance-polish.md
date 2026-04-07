---
type: pr
id: PR-0232
title: "ST-32-06: guest local draft parity, direct-download export, and account-only history affordance polish"
status: ready
owners: "agents"
created: 2026-04-07
updated: 2026-04-07
stories:
  - "ST-32-06"
tags:
  [
    "frontend",
    "backend",
    "klassrumskartan",
    "public-access",
    "guest-workspace",
    "export",
    "history",
  ]
dependencies:
  - "ADR-0079"
  - "ADR-0080"
  - "ST-32-05"
  - "EPIC-29"
  - "PR-0229"
  - "PR-0223"
acceptance_criteria:
  - "Given shared planner toolbar overflow no longer keeps undo/redo visibly pinned after `PR-0229`, when guest users trigger undo or redo from the toolbar or keyboard shortcuts, then grouping and seating undo/redo work as browser-owned local editing state with the same shortcut parity as the authenticated workspace."
  - "Given guest exports grouping or seating work, when the shared export entry point is used, then export delivers an immediate direct download only through dedicated public routes under `/api/v1/public/apps/classroom.group-seating-studio/grouping/export` and `/api/v1/public/apps/classroom.group-seating-studio/seating/export`, and does not render Vault/MyFiles targets, resumable export-job recovery, or other authenticated artifact-history surfaces."
  - "Given guest export may still capture browser-owned checkpoint payloads or descriptors for later authenticated upgrade, when those payloads are stored locally, then they are not treated as guest Smart-history inputs and are not wired to `Use history`."
  - "Given guest mode still needs honest account-only boundaries, when history, recovery, or job affordances render, then authenticated history drawers, job recovery surfaces, and other account-owned continuity affordances stay omitted or minimally blocked according to the frozen surface matrix without any fallback into `/api/v1/apps/classroom.group-seating-studio/...` export, history, recovery, or download routes."
  - "Given authenticated Klassrumskartan already has export-job recovery and server-owned history semantics, when this guest slice ships, then the authenticated export/history flows remain unchanged."
  - "Given new public export helper routes are added for guest continuity, when they are reviewed, then they publish rate limits, payload caps, time budgets, validation rules, and cookie-agnostic semantics consistent with `ADR-0079`."
---

## Problem

After `PR-0223`, the guest browser workspace can author rosters, templates, and
planner drafts, but it still falls short in three places that now matter more
because the guest surface is intentionally reusing the authenticated planner
chrome:

- guest undo/redo is still a no-op even though undo/redo is local editing state
- guest export is still hidden instead of using the same visible export entry
  point with a different transport boundary
- the remaining account-only history and recovery affordances are not yet
  fully frozen in the public shell

Those are one coherent slice because they all define the difference between
guest local continuity and authenticated durable continuity.

## Goal

Finish the honest guest-local continuity layer:

- make guest undo/redo real and keyboard-parity-safe
- add guest direct-download export through the shared entry points
- keep any guest-local checkpoint capture limited to browser-owned continuity or
  later authenticated upgrade
- finish the account-only affordance policy for history, recovery, jobs, and
  artifact surfaces

## Non-goals

- Guest `Regler` enablement or solver-based Smart-run parity
- Reintroducing guest `Use history` or history-based Smart behavior
- Changing authenticated export-job recovery, Vault integration, or
  cross-device continuity
- Silent guest fallthrough into owner-scoped authenticated export/history APIs

## Implementation plan

1. Implement guest local undo/redo.
   - Replace the guest no-op history actions with real browser-owned local
     undo/redo for grouping and seating drafts.
   - Reuse the shared planner shortcut contract established by `PR-0229`.
   - Keep these semantics local editing state only, not authenticated history.

2. Keep history boundaries honest.
   - Do not add guest history drawers or authenticated recovery surfaces.
   - Keep history-based Smart controls out of guest mode per `ADR-0080`.
   - Make sure guest local undo/redo does not imply guest durable history.

3. Add guest direct-download export.
   - Reuse the same visible export entry point where possible.
   - Send guest export through explicit public direct-download routes at:
     - `/api/v1/public/apps/classroom.group-seating-studio/grouping/export`
     - `/api/v1/public/apps/classroom.group-seating-studio/seating/export`
   - Keep those routes outside the authenticated `/api/v1/apps/...` namespace.
   - Do not create resumable job rows, Vault artifacts, or recoverable guest
     export jobs.
   - Do not reuse authenticated export/history/recovery/download routes as
     guest fallbacks.

4. Keep checkpoint capture scoped correctly.
   - If guest export captures checkpoint payloads or descriptors, store them
     only in the browser-owned guest snapshot.
   - Keep that payload lane importable later through the authenticated upgrade
     path.
   - Do not wire those payloads into guest `Use history`, because guest
     `Use history` does not exist.

5. Finish the account-only affordance audit.
   - Remove or block authenticated history/recovery/job/Vault affordances in the
     guest toolbar, drawers, and related presentation seams according to the
     frozen matrix.
   - Keep authenticated flows unchanged.

6. Publish the public export abuse-control contract.
   - Freeze the guest export routes as cookie-agnostic and non-ambient per
     `ADR-0079`.
   - Publish route-level:
     - rate limits
     - payload caps
     - request time budgets
     - validation rules

## Test plan

- `pdm run fe-test` targeted at:
  - guest draft-session/state specs covering undo/redo behavior
  - guest shell specs covering visible omission/blocking of account-only
    history and recovery affordances
  - shared export action specs touched by guest direct-download behavior
- backend and web unit tests for:
  - the new public grouping export route
  - the new public seating export route
  - authenticated-route guardrails proving no fallback into `/api/v1/apps/...`
  - cookie-agnostic public semantics
  - validation failures
  - rate limits, payload caps, and request time budgets
- `pdm run fe-type-check`
- `pdm run docs-validate`
- focused public-route browser proof showing:
  - guest undo/redo works from both toolbar controls and keyboard shortcuts
  - guest export starts immediate download
  - no Vault/MyFiles or resumable recovery UI appears
  - guest export uses only the dedicated public export routes
  - guest export/history flows never call owner-scoped authenticated export or
    history endpoints

## Rollback plan

- Re-hide guest export and revert guest undo/redo changes if the slice leaks
  into authenticated export/history seams or makes guest draft state unreliable.
- Leave authenticated export/history flows untouched during rollback; only the
  guest/public transport and state wiring should move.

## Review gate

- Retained review gate:
  [REV-PR-0231](../reviews/review-pr-0231-guest-smart-parity-and-local-continuity-boundary.md)
