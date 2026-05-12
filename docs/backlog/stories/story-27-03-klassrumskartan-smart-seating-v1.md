---
type: story
id: ST-27-03
title: "Klassrumskartan — Smart seating v1"
status: done
owners: "agents"
created: 2026-03-25
updated: 2026-05-11
epic: "EPIC-27"
dependencies: ["ST-27-01", "ST-27-02", "ST-27-06"]
acceptance_criteria:
  - "Given the teacher is in `Sittplatser` and `Smart` is `off`, when they use `Slumpa`, then seating remains the current random reshuffle behavior."
  - "Given the teacher is in `Sittplatser` and `Smart` is `on`, when they use `Slumpa`, then the planner requests a backend-owned smart seating result instead of a frontend-only random shuffle."
  - "Given the teacher reruns `Slumpa` in `Sittplatser` with `Smart` still `on`, when multiple good rule-respecting seating candidates exist, then the backend prefers a materially different valid result over repeating the current assignment hash."
  - "Given the teacher authors roster-global `Keep apart`, `Keep near`, and `Närmare läraren` rules and enables draft-local `Use history`, when smart seating runs, then those inputs affect the backend result without exposing raw weights, score tables, or rule-engine jargon."
  - "Given the teacher creates or edits smart rules from one seating draft and later opens another draft for the same class, when the second draft loads, then those same roster-global rules are available there without reauthoring them."
  - "Given one seating `Keep apart` cluster exists, when smart seating places those students, then it treats immediate orthogonal or diagonal neighbors as invalid placements, still allows same-row or same-column seating when one full seat buffer remains between them, and prefers extra spacing when the room allows it."
  - "Given one seating `Keep near` pair exists, when smart seating places those two students, then direct left/right or above/below adjacency is the clean target, while diagonal or one-seat-buffer fallback is only used when stronger adjacency is impossible."
  - "Given one seating `Keep near` cluster larger than two students exists, when smart seating places those students, then it prefers one local vicinity for the cluster rather than requiring one exact shoulder-to-shoulder seat pairing."
  - "Given `Use history` is enabled and a student does not have `Närmare läraren`, when smart seating runs across multiple teacher-approved checkpoints, then it tries to balance that student's teacher-distance more fairly over time rather than repeatedly leaving the same students nearest the teacher."
  - "Given room-owned teaching cues exist, when smart seating evaluates teacher-distance, then it infers the teaching/front edge from `Whiteboard` and `Kateder`; if no stronger cue exists, the default teaching position is top-middle in the standard planner view."
  - "Given eligible seating checkpoints exist and `Use history` is enabled, when smart seating runs, then history is derived from those checkpoints rather than from draft autosave or undo/redo mechanics."
  - "Given `Use history` is enabled but no eligible checkpoints exist, when the teacher runs smart seating, then the planner applies a smart result without history, reports `used_history=false`, and does not treat draft autosave or undo/redo mechanics as history."
  - "Given the room or rules make a perfect result impossible, when smart seating completes, then the best available layout is still returned together with one short teacher-facing message rather than a hard failure."
ui_impact: "Yes (smart seating toggle and result flow)"
data_impact: "Yes (smart seating request/response contract)"
---

## Context

The seating workspace already has the right surrounding mechanics: explicit room context, autosave,
undo/redo, history drawers, and export-backed artifacts. This story adds the first smart seating
lane on top of that foundation.

## Notes

- Keep the visible teacher model intentionally small.
- Keep ownership explicit:
  - smart rules are roster-global
  - `Smart` / `Use history` toggles and current arrangement state remain draft-local
- Smart reruns should favor diversity among good candidates without becoming a teacher-facing
  randomness setting.
- `ST-27-07` now owns the dedicated `Regler` workspace and the summary-link cut-over:
  - keep draft-local seating controls such as `Use history` close to `Smart`
  - do not add new primary rule-editing affordances inside `Sittplatser`
  - do not move rule editing into a drawer; task-pane summaries may link to `Regler` only
- `Keep apart` and `Keep near` are cluster rules for 2+ students in V1, not pair-only shortcuts.
- Canonical seating semantics were tightened after `PR-0154` close-out and are now aligned in the
  shipped solver:
  - `Keep near` means one immediate local cluster, with direct left/right or above/below adjacency
    preferred and only constrained fallback loosening
  - for a 2-student `Keep near` pair, diagonal or one-seat-buffer placements are fallback/tradeoff
    results rather than normal successful pair layouts
  - `Keep apart` means meaningful separation, not merely "not touching" or "not in direct
    orthogonal adjacency"
  - immediate orthogonal and diagonal neighbors are invalid for `Keep apart`, while same-row or
    same-column placements remain valid when one full seat buffer stays between the students
  - `Närmare läraren` means nearer the teaching edge first and the teaching zone second, not merely
    nearer one arbitrary point-anchor
- Overlapping visible relationship clusters are intentionally out of scope for V1.
- Recommend that the room includes `Whiteboard` or `Kateder` so teacher-distance-aware smart
  seating has an explicit teaching edge instead of relying only on the default top-middle
  assumption.
- The solver is authoritative on the backend; the frontend should not duplicate the full logic.
- This story depends on `ST-27-06`; do not build smart seating behavior on the old planner-wide
  flush/save-status/shared-timer contract.
- This story is about smart seating behavior, not score-panel explainability or debug surfaces.
- Follow-up UX polish such as alternate smart results and explanation-copy tightening is handled
  separately.

## Implementation Summary (as of 2026-03-28)

- `PR-0154` shipped the backend-owned smart seating run through a dedicated domain solver,
  application handler, and seating-only API endpoint.
- `Slumpa` now branches honestly in `Sittplatser`:
  - `Smart` off keeps the local random reshuffle
  - `Smart` on flushes the draft + smart-rule lanes and applies the backend smart-run result
- Draft-local `Use history` is exposed in the seating workspace and persisted through the draft
  lane. `ST-27-05` / `PR-0316` refines the no-checkpoint first-run case so it runs without history
  instead of blocking, while still excluding drafts and undo/redo from history.
- Real-room topology is now normalized into teacher-facing ranks, contiguous local zones, and
  spread-oriented seating blocks, so `G20` and similar classrooms no longer fall back to toy-grid
  adjacency assumptions.
- `Närmare läraren` now rotates inside the valid teacher pool instead of pinning the same strongest
  seats, 2-student `Keep near` pairs now rerun across direct row/column adjacency rather than
  standard diagonal placement, and `Keep apart` plus rerun diversity now keep every student moving
  across repeated history-enabled smart runs.
- The solver contract is now regression-covered by two classroom-scale scenario suites:
  - `SA24D` / `G20` for mixed `Keep apart`, `Keep near`, and `Närmare läraren`
  - `BF25` / `G104` for an overlapping-rule student who is both `Närmare läraren` and part of one
    `Keep apart` cluster
- Verification now closes with the real `G20` / `SA24D` scenario suite, the `BF25` / `G104`
  overlap suite, focused backend tests, and a live semantics proof on a fresh local backend that
  produced 120 valid reruns with 120 unique layouts, a 12-seat valid teacher pool with 11 seats
  exercised, 10 distinct seats for each near-teacher student, pairwise keep-near row/column
  adjacency rotation, and stricter keep-apart diagonal rejection.
