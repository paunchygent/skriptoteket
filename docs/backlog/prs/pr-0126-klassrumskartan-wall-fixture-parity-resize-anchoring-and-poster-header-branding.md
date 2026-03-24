---
type: pr
id: PR-0126
title: "Klassrumskartan: wall-fixture parity, resize anchoring, and poster header branding"
status: ready
owners: "agents"
created: 2026-03-24
updated: 2026-03-24
stories:
  - "ST-24-04"
  - "ST-26-01"
tags: ["frontend", "backend", "klassrumskartan", "rendering", "export", "ux"]
acceptance_criteria:
  - "Given the teacher edits a classroom with wall fixtures on the left or right wall, when those fixtures render in the builder, then `Dörr` and `Fönster` labels render vertically with the same wall-side semantics used by preview and export."
  - "Given the teacher previews or exports a classroom with side-wall fixtures, when the scene renders, then side-wall `Dörr` and `Fönster` markers remain visibly attached to the wall margin and their labels stay readable instead of collapsing into clipped line artifacts."
  - "Given the classroom poster renders to `A4 landscape` or `A3 landscape`, when the export is laid out, then the classroom scene still uses the maximum practical printable area, remains single-page, and does not lose scene area to oversized branding or side-wall chrome."
  - "Given the seating poster header renders, when the page is viewed, then a subtle Skriptoteket logo watermark appears in the top-right header band with the same edge inset as the left-side title block."
  - "Given the teacher grows or shrinks the room, when a true wall fixture is attached to the right or bottom wall, then it stays attached to that wall after the resize instead of remaining behind on the floor."
  - "Given the teacher places or previews wall fixtures near floor content, when occupancy is evaluated, then wall fixtures continue to render outside the floor area but reserve their boundary span so overlapping wall-plus-floor placement is rejected."
  - "Given adjacent benches or whiteboards are presented in preview/export, when the shared presentation seam runs, then preview/export may still coalesce those fixtures visually while the builder continues editing the underlying raw fixture identities."
---

## Problem

The current wall-fixture behavior has drifted across Klassrumskartan surfaces:

- the classroom builder renders raw wall fixtures and therefore loses the shared
  vertical side-wall label semantics used elsewhere
- preview and export both treat wall fixtures as annotations, but the side-wall
  annotation space is too narrow and clips vertical labels into unreadable
  blueprint-like fragments
- room resize changes only grid dimensions, so right-wall and bottom-wall
  fixtures no longer follow the room edge after growth or shrink
- wall fixtures are visually outside the floor but still share ambiguous
  boundary occupancy with floor content, which allows impossible overlap cases
- the poster header still lacks the approved subtle Skriptoteket branding mark
  even though the export lane is now teacher-facing and artifact-grade

This creates one teacher-visible regression family rather than isolated bugs.
The same room concept currently behaves differently in the builder, preview, and
PDF artifact.

## Goal

Lock one follow-up slice that restores wall-fixture parity and legibility across
the builder, preview, and PDF poster without regressing the current export
strengths:

- builder uses the same wall annotation semantics as preview/export for side
  labels
- preview/export side-wall fixtures remain readable
- true wall fixtures stay attached to resized walls
- wall fixtures reserve their boundary span cleanly
- the poster keeps maximizing classroom visibility on the page
- the poster header gains a subtle Skriptoteket brand watermark only in the
  header band

## Non-goals

- Moving ordinary floor furniture such as benches when the room grows or
  shrinks.
- Reworking the room-template storage model or adding new fixture kinds.
- Adding teacher-selectable poster branding modes or multiple watermark styles.
- Introducing new PDF layouts, orientation choices, or extra poster pages.
- Reopening smart placement or near-wall floor-furniture heuristics.
- Changing the teacher-facing export action flow, polling flow, or download
  flow.

## Locked design decisions

- Split the shared scene behavior into:
  - wall-annotation normalization shared by builder, preview, and export
  - presentation coalescing shared by preview and export only
- The builder must preserve raw fixture identity for editing and deletion; it
  must not coalesce whiteboards or benches into one edit target.
- Left/right wall labels render vertically.
- Top/bottom wall labels render horizontally.
- Side-wall labels must not depend on fitting inside the current tiny wall band;
  the renderer must give them a readable annotation treatment.
- Wall fixtures remain visually outside the floor area.
- Wall fixtures reserve their boundary span for placement/collision, even
  though they do not consume interior floor tiles.
- Only true wall fixtures follow room resize in this slice.
- The seating poster must remain single-page and continue maximizing classroom
  scene real estate on the page.
- The top-right header branding mark must use Skriptoteket branding and remain
  subtle:
  - use the Skriptoteket horizontal logo asset
  - place it in the header band only
  - align it to the same page inset logic as the left-side title block
  - keep it faint gray, approximately 6-10% opacity

## Implementation plan

- Refactor the frontend room presentation seam so wall-annotation normalization
  is reusable independently from fixture coalescing.
- Update the builder surface to consume wall-annotation normalization while
  preserving raw fixture edit identity.
- Keep preview and seating canvas on the full normalized presentation seam so
  coalesced benches/whiteboards still render as one visual object where
  appropriate.
- Add explicit wall-fixture re-anchoring during room resize:
  - left/top fixtures keep origin
  - right fixtures recompute horizontal anchor from the new room width
  - bottom fixtures recompute vertical anchor from the new room height
  - preserve wall-side intent instead of re-inferring loosely after resize
- Tighten boundary occupancy logic so wall fixtures can block conflicting floor
  placements along their reserved boundary span.
- Update the poster renderer so side-wall labels are readable:
  - keep the shrink-to-fit scene model
  - preserve maximum practical scene area
  - add a minimum readable side annotation treatment rather than clipping
    rotated labels into the wall track
- Reuse the existing Skriptoteket horizontal logo asset for a faint top-right
  header watermark in the export-owned HTML/CSS.

## Test plan

- Frontend unit tests:
  - builder-side wall normalization keeps raw fixture ids but applies
    side-label orientation
  - resize re-anchoring keeps right/bottom wall fixtures attached
  - boundary occupancy rejects invalid wall-plus-floor overlap cases
- Frontend surface tests:
  - builder renders vertical side-wall labels
  - preview still coalesces benches/whiteboards correctly
  - seating canvas still renders wall fixtures outside the floor surface
- Backend/export tests:
  - `A4 landscape` and `A3 landscape` remain single-page and preserve the
    fitted scene contract
  - side-wall labels are emitted in a non-clipped readable annotation contract
  - the top-right Skriptoteket watermark is present with the intended alignment
- Live/browser proof:
  - place `Dörr` and `Fönster` on left/right walls in the room editor
  - resize the room wider and taller and confirm true wall fixtures stay
    attached
  - open preview and confirm no wall/floor overlap regressions
  - export PDF and verify side-wall readability plus subtle top-right branding

## Rollback plan

- Revert the wall-fixture parity/remediation pass while preserving the existing
  seating export lane, asynchronous job flow, and artifact download behavior.
