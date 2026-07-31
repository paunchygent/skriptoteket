---
type: story
id: ST-SKRIPT-25-06
title: Flunk-Out Frenzy VPW donor topology and table-spec rebuild
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: active
readiness_review:
  record: inline
  status: not_started
closeout_review:
  record: inline
  status: not_started
epic: EPIC-SKRIPT-25
acceptance_criteria:
- Given repeated board-shape failures from locally-invented geometry, when this story
  is complete, then Flunk-Out Frenzy has a checked-in donor map artifact that captures
  the VPW whole-board boundary grammar and the parts we intentionally borrow.
- Given the compiled pinball-table runtime is now the stable seam, when this story
  is complete, then `prototypeAlphaTableSpec.ts` is rebuilt from the donor topology
  while the compiler, rules, and runtime contracts stay intact.
- Given donor geometry fidelity and donor device-semantic fidelity are separate risks,
  when this story is complete, then topology cutover and semantic-representation follow-up
  stay explicit in linked tasks instead of being blurred together.
- Given donor lanes and launcher corridors are shaped board regions rather than local
  bounding boxes, when this story is complete, then all remaining lane flattening
  seams and `laneBounds` shortcuts are either replaced with donor-shaped lane-region
  semantics or kept open as explicit linked follow-up debt.
- Given future mechanics slices depend on a sane board, when this story is complete,
  then the donor-based board can be inspected manually in-browser before `PR-0193`
  through `PR-0195` continue.
- Given this corrective work will span sessions, when the story is updated, then the
  linked PR task and `.codex/handoff.md` keep the current donor-integration progress
  explicit.
retired_ids:
- ST-25-06
---

## Context

### Context

The current Flunk-Out Frenzy mechanics tranche reached a point where the table
authoring model improved, but the board still drifted visually and structurally
from sane pinball grammar. The extracted VPW ROM example table under
`.artifacts/vpw-rom-example-table-extracted/` gives us a better path: borrow a
coherent whole-board topology donor, convert it into our compiled schema, and
only then resume higher-risk mechanics slices.

This story is intentionally corrective. It does not reopen the browser-owned
runtime decision, the compiled pinball-table seam, or the rule/runtime
ownership boundary from `ST-25-05`. It resets only the authored board
topology.

### Notes

- Keep the donor use explicit:
  - extract a checked-in donor map artifact
  - record exactly which VPW objects feed the rewritten board skeleton
  - preserve which donor semantics are borrowed vs avoided
  - if a donor object exceeds the current schema, track schema expansion explicitly
    instead of flattening the donor object into a simpler local approximation
  - treat donor lanes and launcher corridors as shaped semantic regions, not
    approximate `laneBounds` boxes or other coarse local containment seams
  - keep board carriers on donor drag-point chains instead of collapsing them
    into a local redraw
- Keep the refactor bounded:
  - `PR-0198` owns donor topology and table-spec cutover
  - `PR-0199` owns full donor semantic representation for richer triggers,
    gates, and rollover shapes
  - `PR-0201` owns the lower shooter-corridor corrective split where donor
    `Wall263` currently overlaps the donor shooter-lane walls as a fat physical
    rail and pinches the launch path
  - `PR-0200` owns the Rapier 3D launcher-chain migration where the current
    browser model still wedges on `Wall34` because it flattens donor plunger,
    wall-face, and launcher-height truth into a flat launcher path
  - `PR-0202` owns the full-board donor 3D carrier mapping target, including
    above-playfield metal/wire rails, so board-path fidelity is governed by one
    provenance-explicit donor carrier layer
  - `PR-0203` owns elevated donor rail travel and left-handoff mechanics so the
    launcher path is runtime-driven by donor carriers instead of falling back
    to perimeter bounce behavior
  - sequencing correction from
    `docs/reference/ref-flunk-out-frenzy-physical-rail-architect-direction-2026-04-04.md`:
    no further continuation of `PR-0200`, `PR-0202`, or `PR-0203` may proceed
    until `ST-33-01` establishes the carrier-role schema, launcher-world
    ownership model, and observer/cut-over governance needed to avoid route-
    driven cut-over shortcuts
  - keep the compiler/runtime seam intact
  - do not port VPX/ROM rule code or editor artifacts
- Track progress in the linked PR task:
  - donor map extracted
  - donor-backed spec module added
  - `prototypeAlphaTableSpec.ts` cut over
  - deterministic verification complete
  - manual browser inspection pending or accepted

## Epic Contract Slice

The source material below remains authoritative for this section.

## Contract Inputs

The source material below remains authoritative for this section.

## Live Verification Plan

Verification expectations remain in the retained source material below.

## Non-Goals

The source boundaries and recovery limits remain preserved below.

## Notes

The source material below remains authoritative for this section.

## Decision And Assumption Ledger

The source material below remains authoritative for this section.

## Plan Document Review

The source material below remains authoritative for this section.

## Story Closeout Review

The source material below remains authoritative for this section.
