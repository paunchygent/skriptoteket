---
type: story
id: ST-27-01
title: "Klassrumskartan — Smart-assignment contract reset and control model"
status: in_progress
owners: "agents"
created: 2026-03-25
epic: "EPIC-27"
dependencies: ["EPIC-24"]
acceptance_criteria:
  - "Given the teacher opens the planner after this slice ships, when common smart-assignment controls are shown, then the shared visible smart model is limited to `Support seat`, `Keep apart`, `Keep near`, and `Use history` rather than the previous planner-note / proximity / stability controls."
  - "Given the teacher uses smart grouping, when a grouping-specific room-informed option is shown, then it appears as one explicit mode-specific toggle such as `Ska hur nära de sitter räknas?` rather than as a fifth shared global smart control."
  - "Given the teacher is in `Grupper` or `Sittplatser`, when the main action row renders, then each mode shows one small `Smart` toggle beside `Slumpa`, and new drafts default that toggle to `off`."
  - "Given the teacher turns `Smart` on or off for one active draft, when the draft reloads later, then that mode's toggle state is restored for that draft rather than reset or shared globally."
  - "Given the repo has no real users yet, when this story replaces the older visible metadata model, then the old planner-note / proximity / stability semantics are deleted from the active contract without migration or compatibility shims."
  - "Given `Keep apart` sets and `Keep near` pairs are persisted, when the backend stores them, then the persistence shape is normalized relational storage rather than an anonymous JSON blob."
ui_impact: "Yes (smart toggles + control-model reset)"
data_impact: "Yes (new smart-assignment persistence and contract cleanup)"
---

## Context

The repo already shipped a fundamentals-first planner and explicitly pruned the old solver-era
contract. Before smart placement can return cleanly, the visible control model and persistence
contract need a reset that matches the newly approved product decisions.

## Notes

- Keep `Slumpa` as the primary action surface; do not add a second competing primary smart button.
- Delete the older visible planner-note / teacher-proximity / stability controls rather than
  trying to blend or translate them.
- The small visible model is a product decision, not a temporary UI compromise.
- The relational persistence shape should remain compatible with compiling `keep apart` sets into
  internal pairwise repel edges at solve time.
- This story defines the contract reset; it does not itself deliver the full smart solver.
