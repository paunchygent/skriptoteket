---
type: pr
id: PR-0123
title: "Klassrumskartan: seating scene remediation for wall markers, localization, and print contrast"
status: ready
owners: "agents"
created: 2026-03-24
updated: 2026-03-24
stories:
  - "ST-26-01"
tags: ["frontend", "backend", "klassrumskartan", "export", "rendering", "remediation"]
acceptance_criteria:
  - "Wall markers such as windows, doors, and whiteboards render as wall annotations outside the classroom floor rather than collapsed into the room surface."
  - "Fixture labels are localized to Swedish where appropriate and remain consistent between preview and export."
  - "Adjacent benches and whiteboards coalesce at presentation time into one labeled visual object with the label centered across the merged span."
  - "The seating poster and its preview are optimized for grayscale printing first: white floor/background, strong contrast, and no beige room field that reduces legibility."
  - "The in-scope surfaces for this slice — overview preview, seating preview surface, and export renderer — all follow the same locked presentation-normalization rules."
---

## Problem

The first shipped seating export lane works end to end, but the current scene
presentation is visibly wrong in several important ways:

- wall markers such as windows are collapsed into the classroom floor instead of
  rendered on the wall
- wall text placement is wrong for side walls
- fixture labels are still partly in English
- repeated bench and whiteboard labels create clutter instead of reading as one
  continuous object
- the beige floor/background reduces grayscale print contrast

These issues also show up in preview, which means this is a shared
presentation/remediation problem rather than an export-only CSS bug.

## Goal

Remediate the shared seating scene presentation so preview and export both read
like a clean, blueprint-like classroom poster with correct wall annotations,
localized labels, coalesced fixtures, and grayscale-first contrast.

## Non-goals

- Redesigning the underlying classroom-planner domain model or stored template
  geometry.
- Introducing new export layouts or a layout picker.
- Changing the teacher-facing export workflow introduced in `PR-0120`.
- Changing room-template editing semantics; fixture storage/editing remains
  independently editable even when presentation coalesces output.
- Fixing every export/test follow-up discovered in adjacent slices; only the
  rendering-related items explicitly listed in this PR are in scope.

## In-scope surfaces

- Overview preview surface
- Seating preview surface
- Seating export renderer/poster output

Out of scope:

- Room-template editor/builder rendering unless a shared normalization seam
  makes it unavoidable
- unrelated toolbar/export UX behavior

## Locked design decisions

- Preview and export should share the same presentation rules for fixture labels,
  wall annotations, and coalescing; do not fix export alone and leave preview
  wrong.
- This PR must lock one shared presentation-normalization seam that owns:
  - wall-annotation placement
  - coalescing rules
  - normalized rendered fixture labels
  Both preview and export must consume that seam rather than duplicating
  heuristics independently.
- Wall markers belong to wall margins/annotation space, not to the classroom
  floor area.
- Left and right wall labels should render vertically.
- Top wall labels remain horizontal.
- Bottom-wall labels, if present, remain horizontal and render outside the room
  floor in the bottom wall margin; do not infer a different orientation ad hoc.
- Grayscale printing is the primary readability target: page background and room
  floor should be white, with contrast coming from linework, typography, and a
  few controlled accents.
- Adjacent same-type fixtures that form one continuous visual object should
  coalesce at presentation time only; editing/storage remain independently
  editable.
- Coalesced label placement must be centered against the merged bounds, not any
  one child segment.
- Coalescing never merges across corners, wall-side changes, or visible gaps.

## Canonical rendered label map

The shared presentation-normalization seam must define one canonical rendered
label source for this slice. Use a normalized display-label layer rather than
letting each surface choose independently between stored labels and raw fixture
kind.

Visible fixture labels in scope:

- `door` -> `Dörr`
- `bench` -> `Bänk`
- `window` -> `Fönster`
- `whiteboard` -> `Whiteboard`

The PR implementation must also define the intended Swedish/explicit label for
any additional visible fixture type already rendered in the affected surfaces
for this slice, or explicitly mark that fixture as intentionally unlabeled.

## Remediation items in scope

### Shared scene presentation defects

- Move windows, doors, and whiteboards to wall-annotation placement outside the
  classroom floor.
- Render left/right wall labels vertically.
- Keep top wall labels horizontal.
- Keep bottom wall labels horizontal.
- Localize fixture labels consistently:
  - `door` -> `Dörr`
  - `bench` -> `Bänk`
  - `window` -> `Fönster`
  - keep `Whiteboard` as `Whiteboard`
- Coalesce adjacent benches into one visual object with one centered `Bänk`
  label.
- Coalesce adjacent whiteboards into one visual object with one centered
  `Whiteboard` label.
- Replace the beige floor/background with a white, high-contrast
  grayscale-first surface.
- Keep preview/export parity explicit: any drift across the in-scope surfaces is
  considered a failure for this PR.

## Coalescing invariants

### Benches

- Benches coalesce only when they are collinear on the same row.
- They must have touching horizontal bounds with no gap.
- They never merge across rows or corners.
- The rendered label is one centered `Bänk` label on the full merged bounding
  box.

### Whiteboards

- Whiteboards coalesce only when they attach to the same wall side.
- They must have touching spans with no gap and the same wall depth/orientation.
- They never merge across corners, across different wall sides, or across gaps.
- The rendered label is one centered `Whiteboard` label on the full merged
  bounding box.

### Windows and doors

- Windows and doors do not coalesce in this slice unless the implementation doc
  is explicitly updated to define their merge rules first.
- Their primary remediation is wall-margin placement and correct orientation,
  not span-merging.

## Options considered

### Option 1: Fix export HTML/CSS only

Pros:
- Smaller immediate patch.

Cons:
- Preview stays wrong.
- Duplicates presentation logic and invites future drift.

### Option 2: Fix shared preview/export presentation rules

Pros:
- Correct seam and the cleanest long-term result.
- One visual language across overview/preview/export.

Cons:
- Touches both frontend presentation and export translation/rendering.

## Recommendation

Choose Option 2. This is a shared scene-presentation remediation slice, not an
export-only CSS tweak.

## Implementation plan

- Introduce or designate one shared presentation-normalization seam for wall
  annotation placement, coalescing, and localized display labels.
- Define deterministic wall-annotation placement so wall markers render in the
  wall margin instead of the floor area.
- Add shared normalized display-label rules for Swedish localization.
- Add presentation-time coalescing for benches and whiteboards using the locked
  invariants above.
- Center coalesced labels against the merged bounds.
- Update overview preview, seating preview, and export renderer to use the same
  normalization seam.
- Switch the poster/preview floor field to white and tune contrast for
  grayscale-friendly printing.

## Follow-ups deliberately out of scope

- jsdom download warning cleanup
- export filename-proof strengthening outside the rendering-specific assertions
- any unrelated export workflow polish not required by this rendering seam

## Test plan

- Focused tests at the shared presentation-normalization seam for:
  - wall placement/orientation
  - canonical label mapping
  - bench coalescing
  - whiteboard coalescing
  - non-merge gaps/corners
  - unequal-span centering on merged bounds
- Focused surface tests proving the overview preview, seating preview, and
  export renderer all consume that seam correctly.
- Dedicated visual/browser proof that exercises corrected wall annotations and
  coalesced whiteboards/benches on each in-scope surface.

## Rollback plan

- Revert the presentation remediation while preserving the export lane and
  teacher-facing export affordance.
