---
type: story
id: ST-27-03
title: "Klassrumskartan — Smart seating v1"
status: ready
owners: "agents"
created: 2026-03-25
epic: "EPIC-27"
dependencies: ["ST-27-01", "ST-27-02"]
acceptance_criteria:
  - "Given the teacher is in `Sittplatser` and `Smart` is `off`, when they use `Slumpa`, then seating remains the current random reshuffle behavior."
  - "Given the teacher is in `Sittplatser` and `Smart` is `on`, when they use `Slumpa`, then the planner requests a backend-owned smart seating result instead of a frontend-only random shuffle."
  - "Given the teacher sets `Support seat`, `Keep apart`, `Keep near`, and `Use history`, when smart seating runs, then those inputs affect the backend result without exposing raw weights, score tables, or rule-engine jargon."
  - "Given eligible seating checkpoints exist and `Use history` is enabled, when smart seating runs, then history is derived from those checkpoints rather than from draft autosave or undo/redo mechanics."
  - "Given `Use history` is enabled but no eligible checkpoints exist, when the teacher tries to run smart seating, then the planner does not silently fall back to no-history behavior and instead blocks that history-enabled run with a short teacher-facing explanation."
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
- The solver is authoritative on the backend; the frontend should not duplicate the full logic.
- This story is about smart seating behavior, not score-panel explainability or debug surfaces.
- Follow-up UX polish such as alternate smart results and explanation-copy tightening is handled
  separately.
