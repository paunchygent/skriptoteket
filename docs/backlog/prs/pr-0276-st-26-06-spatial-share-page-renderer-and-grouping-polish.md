---
type: pr
id: PR-0276
title: "ST-26-06 spatial share-page renderer and grouping polish"
status: done
owners: "agents"
created: 2026-04-30
updated: 2026-05-01
stories:
  - "ST-26-06"
tags: ["backend", "frontend", "renderer", "klassrumskartan", "sharing", "mockup"]
dependencies:
  - "PR-0274"
acceptance_criteria:
  - "Given anyone opens a seating share link, when the artifact is active, then the page renders a real spatial classroom map with room fixtures, benches, seats, empty seats, and placed students rather than a row/place card grid."
  - "Given the shared seating page is viewed at desktop and phone widths, when visually inspected, then it follows the approved spatial-map mockup and remains readable without editor chrome or app APIs."
  - "Given the shared seating page must remain a static exported artifact, when responsive layout is implemented, then sizing and fit behavior are CSS-only with no JavaScript calculations, resize listeners, or inline runtime measurement scripts."
  - "Given grouping share links remain card-based, when grouping pages render, then their cards receive responsive spacing, hierarchy, and print polish consistent with the share-page visual language."
  - "Given hostile class, room, group, fixture, or student text exists, when share pages render metadata and body content, then escaping, no-script behavior, `noindex,nofollow`, and cache policy remain covered by contract tests."
  - "Given this is a visual rendering correction, when the slice is reviewed, then design acceptance is based on visual inspection screenshots against `docs/mockups/st-26-06-share-link-ux-and-page-renderer/shared-seating-page-spatial-map-mockup.png`, while automated tests cover security/provenance and renderer contracts only."
  - "Given adjacent benches are coalesced into one merged poster-scene fixture with label `Bänk`, when the static seating share page renders the fixture, then the bench body spans the merged geometry and the label is centered as an overlay over the full bench span."
  - "Given PR-0276 visual proof is refreshed, when desktop and mobile seating screenshots are saved, then the fixture set includes at least one labeled merged bench so the screenshot evidence covers the centered-label contract."
---

## Problem

The current share renderer technically emits responsive HTML/CSS, but seating
shares are rendered as generic cards with `Rad` and `plats` text. That is not a
classroom map and does not meet the product direction for shareable seating
plans.

## Goal

Reuse or extract the existing poster/room-scene rendering model so seating
share pages preserve spatial classroom structure: whiteboard, teacher desk,
door, benches, seats, empty seats, and students. Keep grouping pages as cards,
but improve their responsive and print presentation.

## Non-goals

- No change to share-token authorization, slug semantics, ownership, TTL, or
  revocation rules.
- No live draft sharing.
- No SPA/editor controls or JavaScript sizing logic on share pages.
- No visual-quality claims from structural tests alone.

## Implementation plan

1. Extract share-page-safe room-scene rendering from the existing poster
   renderer or create a shared renderer helper that consumes the canonical
   poster scene.
2. Replace the seating share card grid with a spatial classroom scene using the
   prepared seating export contract.
3. Add responsive desktop/mobile CSS for the share page. Layout fit must be
   CSS-only: no `<script>`, resize listener, DOM measurement, or runtime scale
   calculation in the exported artifact.
4. Preserve renderer provenance, presentation hash, content hash, escaping,
   metadata, and cache behavior.
5. Polish grouping share card layout so it belongs to the same share-page
   family.

## Test plan

- Renderer/security tests for escaping, no scripts, robots metadata, cache
  headers, provenance, and content hashes.
- Contract tests proving seating share HTML is produced from the canonical
  poster/room-scene model.
- Renderer-level regression test using a normalized merged bench fixture with
  label `Bänk`; assert the generated markup/CSS supports absolute bench-body
  geometry and an absolute centered label overlay rather than flex sibling
  layout.
- Renderer-level regression tests for wall fixtures: a top whiteboard must sit
  above the floor band with wall-band thickness, and `placement=WALL` without
  `wall_side` must fail closed instead of falling back to floor-tile geometry.
- Browser screenshots at desktop and phone widths for visual inspection against
  the approved mockup, with the rendered artifact asserting no `<script>` tags
  and the fixture set including the labeled merged bench plus a top wall
  whiteboard with `wall_side=TOP`.
- `pdm run typecheck`
- Focused backend renderer/share route tests.
- `pdm run docs-validate`
- `git diff --check`

## Implementation Notes

### Reopened Remediation

- `REV-PR-0276` reopened this slice after review found the data/model path was
  correct but the static renderer was wrong for labeled merged benches.
- Fix applied in `share_scene_renderer.py`: `.room-fixture--bench` is now a
  positioned block fixture, `.room-bench-body` is absolute/inset, and the
  fixture label is an absolute centered overlay for bench fixtures.
- Test added in
  `tests/unit/infrastructure/curated_apps/apps/classroom_planner/test_share_renderer.py`:
  a seating renderer case with a normalized merged bench fixture labeled
  `Bänk` asserts the overlay CSS and merged fixture markup.
- Visual proof refreshed under `.artifacts/pr-0276-spatial-share-renderer/`:
  `sample-share.html`, `desktop.png`, and `mobile.png` include the merged
  labeled bench; the proof asserted no scripts, no horizontal document
  overflow, centered label geometry, and a body spanning the merged bench.
- Second renderer defect fixed in `_fixture_frame()`: `placement=WALL` without
  `wall_side` now raises instead of rendering with floor geometry. The refreshed
  `sample-share.html` uses `wall_side=TOP` and proves the whiteboard top is
  above the floor top with wall-band height.

- Added a dedicated static seating share-scene renderer helper:
  `src/skriptoteket/infrastructure/curated_apps/apps/classroom_planner/share_scene_renderer.py`.
- Seating share pages now render from the canonical `poster_scene` as a
  spatial classroom map with room floor, wall fixtures, teacher desk, benches,
  occupied seats, and empty seats.
- Occupied seats render as larger circular tokens centered on first name plus
  surname when it fits, or surname initial for long surnames. Empty seats render
  as a plain dashed circle with no visible text. Seat row/place numbering is not
  shown on the shared page.
- The seating share artifact emits no JavaScript. Responsive fit is CSS-only
  through percentage geometry, `aspect-ratio`, `min()`, `clamp()`, and media
  queries.
- Added a dedicated static grouping share-card renderer helper:
  `src/skriptoteket/infrastructure/curated_apps/apps/classroom_planner/share_group_renderer.py`.
- Grouping shares now follow
  `docs/mockups/st-26-06-share-link-ux-and-page-renderer/shared-groups-page-mockup.html`:
  serif page title, two-column desktop card grid, single-column mobile stack,
  group member counts, and circular numbered student markers.
- Seating and grouping share pages now use explicit page variant classes so the
  grouping page keeps the approved `1200px` card shell while seating keeps the
  wider spatial-map shell.

## Verification

- `pdm run pytest -q tests/unit/infrastructure/curated_apps/apps/classroom_planner/test_share_renderer.py`
- `PYTHONPATH=src pdm run python - <<'PY' ...` one-off PR-0276 visual proof:
  regenerated `.artifacts/pr-0276-spatial-share-renderer/sample-share.html`,
  `desktop.png`, and `mobile.png` with a merged labeled bench; asserted no
  `<script>`, no horizontal document overflow, centered label geometry, visible
  mobile label, bench body span, and top whiteboard geometry above the floor
  band with wall-band height.
- `pdm run lint`
- `pdm run typecheck`
- `pdm run docs-validate`
- `git diff --check`
- Static visual proof generated sample seating share HTML plus desktop/mobile
  screenshots under `.artifacts/pr-0276-spatial-share-renderer/`; the proof
  asserted one room surface, expected seats, no `<script>` tags, and no
  horizontal document overflow at desktop or phone widths.
- Static visual proof generated sample grouping share HTML plus desktop/mobile
  screenshots under `.artifacts/pr-0276-spatial-share-renderer/`; the proof
  asserted four group cards, expected desktop/mobile grid columns, no
  `<script>` tags, no legacy `group-list` markup, and no horizontal document
  overflow.

## Rollback plan

Restore the prior static share renderer while keeping existing share artifacts
and routes available.
