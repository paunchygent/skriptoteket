---
type: pr
id: PR-0275
title: "ST-26-06 share-link popover and bottom-sheet management"
status: ready
owners: "agents"
created: 2026-04-30
updated: 2026-04-30
stories:
  - "ST-26-06"
tags: ["frontend", "ux", "klassrumskartan", "sharing", "mockup"]
dependencies:
  - "PR-0274"
acceptance_criteria:
  - "Given the authenticated teacher is in `Grupper` or `Sittplatser`, when they open share-link management on desktop, then `Dela` opens an anchored popover matching the approved mockup rather than rendering detached stacked panels above the workspace."
  - "Given the authenticated teacher is on a phone-sized viewport, when they open share-link management, then the same information model opens as a bottom sheet with mobile-sized touch targets."
  - "Given active owned links exist for the current draft, when the popover or bottom sheet opens, then active links are listed compactly with copy and revoke actions."
  - "Given a link is revoked, when the revoke succeeds, then the link leaves the active list immediately and user feedback is delivered through a toast/snackbar affordance rather than a persistent dead row."
  - "Given share-link management changes visible workspace layout, when the slice is reviewed, then visual inspection compares desktop and mobile screenshots against `docs/mockups/st-26-06-share-link-ux-and-page-renderer/share-popover-and-bottom-sheet-mockup.png`."
---

## Problem

The authenticated share-link foundation exposes durable owned shares, but the
current UI renders them as detached panels stacked into the workspace. That
competes with the planning surface and scales badly as links accumulate.

Revoked links currently remain visible as disabled rows, which makes the
workspace feel stale and contradicts the desired active-list mental model.

## Goal

Replace the detached share panels with a compact `Dela` management surface:
desktop uses an anchored popover and mobile uses a bottom sheet. Keep only
active links visible and use toast/snackbar feedback for copy and revoke
outcomes.

## Non-goals

- No backend share-artifact schema change unless undo-safe revoke requires a
  narrowly scoped support field.
- No public guest share flow changes.
- No redesign of the public share page renderer; that belongs to `PR-0276`.
- No generic Vault sharing model.

## Implementation plan

1. Remove the default `PlannerShareLinksPanel` after-toolbar placement from the
   grouping and seating workspace surfaces.
2. Add a share-management trigger to the export/action cluster without a
   notification/count badge; link state belongs inside the management surface.
3. Implement one shared management component that renders as an anchored
   popover on desktop and a bottom sheet on small screens.
4. Filter revoked links out of the visible management list.
5. Replace persistent copied/revoked rows with toast/snackbar feedback.
6. Preserve existing create/list/copy/revoke API contracts from `PR-0274`.

## Test plan

- Focused frontend tests for open/close, active-link filtering, and copy/revoke
  intents.
- Browser screenshots at desktop and phone widths for visual inspection against
  the approved mockup.
- `pdm run fe-type-check`
- `pdm run fe-lint`
- `pdm run docs-validate`
- `git diff --check`

## Implementation notes

- `PlannerShareLinksPanel` is now the shared `Dela` management trigger plus
  surface: desktop renders an anchored popover, and mobile renders the same
  information model as a bottom sheet.
- The active-link list is row-based, not table-like: no `Namn`/`Status`/
  `Åtgärder` header labels and no copied/status pill competing with toast
  feedback.
- Grouping and seating toolbars keep `Dela` in the secondary action cluster
  beside export while the existing overflow ladder still moves lower-priority
  setup/smart controls into the overflow menu under width pressure.
- Revoked shares are filtered out of the visible management list; no archive
  of dead links is shown.
- The toolbar trigger intentionally has no count/notification badge.

## Rollback plan

Restore the existing after-toolbar share panel and keep the share creation API
unchanged.
