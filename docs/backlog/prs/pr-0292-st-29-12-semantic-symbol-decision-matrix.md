---
type: pr
id: PR-0292
title: "ST-29-12: semantic symbol decision matrix"
status: done
owners: "agents"
created: 2026-05-04
updated: 2026-05-04
stories:
  - "ST-29-12"
tags: ["frontend", "docs", "design-system", "icons", "klassrumskartan"]
dependencies:
  - "EPIC-29"
  - "PR-0291"
acceptance_criteria:
  - "Given a repeated action or domain concept has an approved symbol, when a developer implements it, then the decision matrix provides one wrapper or component target."
  - "Given a symbol is rejected for a concept, when future work considers it, then the matrix records why it should not be reused."
  - "Given `IconLink2` is considered for a non-link concept, when the matrix is applied, then it is reserved for actual link/share semantics unless a future approved decision changes that."
  - "Given a current shared wrapper uses a hand-authored SVG, when the matrix is applied, then the custom SVG has either a locked Lucide replacement or a documented exception requiring a compatible add-on library."
---

## Problem

The project needs a deliberate symbol vocabulary before runtime changes. A
visual inventory alone does not prevent future drift unless the accepted,
rejected, and deferred symbols are recorded as semantic decisions.

## Goal

Create the canonical semantic decision matrix for shared and Klassrumskartan
symbols.

The matrix must decide symbols for:

- common global actions and buttons
- Klassrumskartan workspace/domain semantics
- other repeated site/app semantics that already have visible icon usage

## Non-goals

- Runtime implementation.
- Tooltip behavior changes.
- New layout, color, or breakpoint changes.

## Implementation Plan

1. Use the `PR-0291` visual index as the decision surface.
   Include the linked Iconify fallback board as research evidence only.
2. Extend the reference with tables for:
   - approved semantic slot
   - approved icon wrapper/component
   - rejected alternatives and reason
   - scope of use
   - migration target files or surfaces
3. Explicitly resolve known conflicts:
   - link/share versus keep-near
   - teacher anchor versus classroom/building
   - group mode versus student list
   - seating mode versus presentation/map symbols
   - file type symbols versus download action symbols
4. Mark any unresolved symbols as deferred with the reason and required future
   evidence.
5. Record whether any Lucide Lab or Tabler fallback is accepted for a specific
   semantic slot. Do not add broad fallback-library approval without a named
   semantic decision.

## Locked Decisions Already Captured

The global action tranche is approved in
`REF-symbol-semantics-inventory-and-decision-contract-2026-05-04`. It reserves
`IconLink2` for actual link/share semantics, adds required wrapper targets for
copy and file-type icons, and sets `IconX` as the close/dismiss symbol with a
compact low-chrome default treatment across desktop and small screens.

The Klassrumskartan domain-symbol tranche is also approved in the reference.
It separates `Översikt` from `Klasslista`, separates `Grupper` from `Elever`,
reserves `IconLink2` away from proximity rules, and accepts Tabler only for the
named `Grupper` (`users-group`) and `Klassrum` (`chalkboard-teacher`) slots.

The other site/app tranche and final `PR-0293` code-facing wrapper map are
approved in the reference. They cover catalog, vault/files, run/debug/editor,
profile/account, role/permission, AI, spinner, and direct-import migration
targets.

The custom SVG replacement map is already locked in
`REF-symbol-semantics-inventory-and-decision-contract-2026-05-04`:

| Current wrapper | Locked replacement |
|---|---|
| `IconAdjustments` | `SlidersHorizontal` |
| `IconFitView` | `Fullscreen` behind the existing fit-view wrapper name |
| `IconMinus` | `Minus` |
| `IconZoomIn` | `ZoomIn` |
| `IconZoomOut` | `ZoomOut` |

`PR-0292` should preserve these as accepted decisions while completing the rest
of the semantic matrix. No compatible EdTech add-on icon library is needed for
the currently known custom SVG wrappers.

The Iconify fallback board generated in `PR-0291` is available only to compare
Lucide Lab and Tabler candidates for HuleEdu semantic families. It must not be
treated as runtime dependency approval.

## Test Plan

- `pdm run docs-validate`
- `git diff --check`

## Implementation Summary

This slice is complete.

- Added the approved global action matrix to
  `REF-symbol-semantics-inventory-and-decision-contract-2026-05-04`.
- Added the approved Klassrumskartan domain-symbol matrix, including explicit
  rejects for overloaded `IconLink2`, `IconSettings`, `IconPresentation`,
  `IconSchool`, `IconGraduationCap`, `Unlink2`, `IconUsersRound`, and
  `IconClipboardList` in the wrong semantic slots.
- Added the approved other site/app matrix for catalog, vault/files, run
  action/history, debug, code/editor, profile/account, roles/permissions, AI,
  spinner, and the password visibility local leaf exception.
- Added the final `PR-0293` code-facing wrapper map.
- Preserved Tabler as a named fallback exception only for `Grupper` and
  `Klassrum`.

## Verification

- `pdm run handoff-validate`
- `pdm run docs-validate`
- `git diff --check`

## Rollback Plan

Revert the matrix edits while keeping the visual inventory if the decision set
needs another product review round.
