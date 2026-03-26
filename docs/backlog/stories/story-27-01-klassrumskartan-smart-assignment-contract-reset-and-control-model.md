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
  - "Given the teacher opens the planner after this slice ships, when common smart-assignment controls are shown, then the primary smart authoring surface is a class-wide visual workspace flow with `Keep apart`, `Keep near`, and `Use history` rather than the previous planner-note / proximity / stability controls or per-student drawer editing."
  - "Given the teacher is in `Sittplatser`, when seating-specific smart controls are shown, then `Närmare läraren` appears as a seating-only rule on the class-wide visual rule surface rather than as hidden student metadata."
  - "Given the teacher authors relationship rules from the class-wide smart surface, when they create `Keep apart` or `Keep near`, then those rules are created from a temporary multi-student selection plus explicit commit, while `Närmare läraren` remains a unary click-to-toggle rule."
  - "Given the teacher tries to place one student into multiple visible relationship clusters, when they attempt to commit the later rule, then V1 blocks overlapping `Keep apart` / `Keep near` cluster membership rather than trying to resolve competing relation graphs in the UI."
  - "Given the teacher uses smart grouping, when a grouping-specific room-informed option is shown, then it appears as one explicit mode-specific toggle such as `Ska hur nära de sitter räknas?` rather than as a fifth shared global smart control."
  - "Given the teacher is in `Grupper` or `Sittplatser`, when the main action row renders, then each mode shows one small `Smart` toggle beside `Slumpa`, and new drafts default that toggle to `off`."
  - "Given the teacher turns `Smart` on or off for one active draft, when the draft reloads later, then that mode's toggle state is restored for that draft rather than reset or shared globally."
  - "Given the repo has no real users yet, when this story replaces the older visible metadata model, then the old planner-note / proximity / stability semantics are deleted from the active contract without migration or compatibility shims."
  - "Given `Keep apart` sets, `Keep near` relations, and seating-only `Närmare läraren` preferences are persisted, when the backend stores them, then the persistence shape is normalized relational storage rather than an anonymous JSON blob."
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
- Demote the student metadata drawer to an advanced notes/history surface rather than using it as
  the main smart-rule editor.
- The first visual rule-authoring model is intentionally simple:
  - one active tool at a time
  - relation tools use 2+ student temporary selections plus explicit commit
  - `Närmare läraren` toggles directly on click
  - overlapping relationship clusters are blocked in V1
- The relational persistence shape should remain compatible with compiling `keep apart` sets into
  internal pairwise repel edges at solve time.
- This story defines the contract reset; it does not itself deliver the full smart solver.
