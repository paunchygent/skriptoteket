---
type: story
id: ST-25-06
title: "Flunk-Out Frenzy VPW donor topology and table-spec rebuild"
status: in_progress
owners: "agents"
created: 2026-04-02
epic: "EPIC-25"
dependencies: ["ST-25-05", "PR-0191"]
acceptance_criteria:
  - "Given repeated board-shape failures from locally-invented geometry, when this story is complete, then Flunk-Out Frenzy has a checked-in donor map artifact that captures the VPW whole-board boundary grammar and the parts we intentionally borrow."
  - "Given the compiled pinball-table runtime is now the stable seam, when this story is complete, then `prototypeAlphaTableSpec.ts` is rebuilt from the donor topology while the compiler, rules, and runtime contracts stay intact."
  - "Given future mechanics slices depend on a sane board, when this story is complete, then the donor-based board can be inspected manually in-browser before `PR-0193` through `PR-0195` continue."
  - "Given this corrective work will span sessions, when the story is updated, then the linked PR task and `.agents/handoff.md` keep the current donor-integration progress explicit."
ui_impact: "Yes (the playable board topology is rebuilt around donor geometry)"
data_impact: "No (reference donor assets only)"
---

## Context

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

## Notes

- Keep the donor use explicit:
  - extract a checked-in donor map artifact
  - record exactly which VPW objects feed the rewritten board skeleton
  - preserve which donor semantics are borrowed vs avoided
  - keep board carriers on donor drag-point chains instead of collapsing them
    into a local redraw
- Keep the refactor bounded:
  - swap the authored table spec
  - keep the compiler/runtime seam intact
  - do not port VPX/ROM rule code or editor artifacts
- Track progress in the linked PR task:
  - donor map extracted
  - donor-backed spec module added
  - `prototypeAlphaTableSpec.ts` cut over
  - deterministic verification complete
  - manual browser inspection pending or accepted
