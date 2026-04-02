---
type: pr
id: PR-0198
title: "Flunk-Out Frenzy: VPW donor topology extraction and table-spec cutover"
status: in_progress
owners: "agents"
created: 2026-04-02
updated: 2026-04-02
stories:
  - "ST-25-06"
tags: ["frontend", "games", "physics", "table-authoring"]
dependencies:
  - "PR-0191"
acceptance_criteria:
  - "A checked-in donor map artifact captures the VPW whole-board boundary grammar, lower-third lane fork, shooter corridor, and gate or kicker anchors we are borrowing."
  - "`prototypeAlphaTableSpec.ts` is rebuilt from a donor-backed board skeleton instead of locally-invented lane geometry."
  - "The compiled pinball-table system, rules layer, and runtime continue unchanged apart from consuming the new authored table spec."
  - "Focused verification plus a fresh reviewer pass document whether the donor cutover is ready for manual browser inspection."
---

## Problem

The current `PR-0192` implementation improved physics seams, but the authored
board geometry remained unreliable. That makes later mechanics slices too risky
because capture devices, ramps, and objective controllers would sit on top of a
board users already read as broken.

## Goal

Replace the invented board skeleton with a coherent donor-backed topology while
preserving the new compiled runtime seam:

- extract a narrow donor map from the VPW example table
- rebuild `prototypeAlphaTableSpec.ts` around that donor grammar
- keep rules/runtime on the compiled system
- make the result easy to inspect manually in-browser

## Non-goals

- No direct import of VPX or ROM rule code.
- No broad runtime/compiler redesign beyond what the donor-backed spec needs.
- No `PR-0193` capture/eject/save expansion in this task.

## Implementation plan

- Add a donor-map artifact under `data/pinball_resources_and_repos/` summarizing
  the borrowed VPW topology carriers and the schema mapping.
- Add a typed donor-map module under
  `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/table/`
  so board anchors stay traceable to donor sources.
- Rebuild
  `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/table/prototypeAlphaTableSpec.ts`
  to consume the donor-backed skeleton.
- Keep the visible wall and lane carriers on donor drag-point chains instead of
  compacting them into a local redraw, so the board stays donor-derived instead
  of turning into another stitched hybrid.
- Keep the compiled table, physics world, rule engine, and runtime contracts
  intact unless the donor cutover exposes a concrete contract bug.
- Run focused verification and a fresh `skriptoteket_reviewer` pass.

## Test plan

Automated:

- `pdm run fe-type-check`
- `pdm run fe-build`
- `pdm run docs-validate`

Manual/live:

- inspect the donor-backed board manually in-browser before continuing
  `PR-0193`

## Rollback plan

- Restore the previous authored table spec while leaving the compiled
  pinball-table system intact.
- Keep the donor artifact and story/task tracking docs so the corrective work
  remains inspectable for the next attempt.
