---
type: reference
id: REF-SKRIPT-MOCKUP-st-29-small-screen-workspace-redesign-direction
title: ST-29 small-screen workspace redesign direction
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: active
reference_kind: mockup
summary: '# ST-29 Small-Screen Workspace Redesign Direction'
---

## Intent

### Source: Purpose

Retain the approved direction for the renewed `EPIC-SKRIPT-29` small-screen companion
lane.

The mockup shows that the phone layout is not a compressed desktop rail. The
active workspace is shown as a compact primary mode affordance, and all modes
are reached through a `Lägen` bottom sheet. Each workspace receives its own
reduced composition instead of inheriting the same cramped segmented control.

## Package Manifest

### Source: Assets

- [Small-screen workspace mode-sheet mockup](small-screen-workspaces-mode-sheet-mockup.png)

## Design Interpretation

### Source: Direction

- No four-option segmented rail on phone.
- The active workspace is visible in the top control row.
- `Lägen` opens a bottom sheet listing `Översikt`, `Grupper`, `Sittplatser`,
  and `Regler`.
- `Oversikt`, `Grupper`, `Sittplatser`, and `Regler` each need a dedicated
  reduced layout rather than one generic stacked version of desktop.

## Runtime And Proof Boundary

The source does not state a separate runtime and proof boundary.

## Governing Links And Follow-Up

The source does not record separate governing links or follow-up.
