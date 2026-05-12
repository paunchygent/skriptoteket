---
type: story
id: ST-27-05
title: "Klassrumskartan — Smart explanations and rerun messaging"
status: ready
owners: "agents"
created: 2026-03-25
updated: 2026-05-12
epic: "EPIC-27"
dependencies: ["ST-27-03", "ST-27-04", "ST-27-07"]
acceptance_criteria:
  - "Given a teacher has run smart seating or smart grouping, when the result is shown, then the UI presents a short teacher-language explanation rather than raw scores, weights, or debug output."
  - "Given the teacher wants another smart result after a smart run, when `Smart` remains enabled and they use `Slumpa` again, then the UI keeps that same primary action instead of introducing a separate alternate-result button."
  - "Given the teacher reruns smart `Slumpa` but the valid search space is genuinely narrow, when the planner cannot find a materially different strong candidate, then it may show one short teacher-facing message that the current rules leave little room for variation."
  - "Given no eligible checkpoints exist while `Use history` is selected, when the teacher runs smart seating or smart grouping, then the planner applies a smart result without history, returns `used_history=false`, and shows the normal smart-run feedback instead of a warning or blocked run."
  - "Given eligible export/share checkpoints exist while `Use history` is selected, when smart seating or smart grouping runs for the matching roster/context, then the planner loads the checkpoint-history window, returns `used_history=true`, and keeps the history-aware solver behavior covered."
  - "Given no eligible checkpoints exist while `Use history` is selected, when smart assignment soft-degrades to no-history mode, then draft autosave, undo/redo state, history-drawer drafts, abandoned drafts, and public guest local state are not used as history substitutes."
  - "Given the solver cannot satisfy every rule, when the best available result is shown, then the teacher sees one short best-effort message and not a solver-jargon error surface."
ui_impact: "Yes (teacher-language explanation and rerun messaging)"
data_impact: "No"
---

## Context

The product goal is not only stronger assignment quality but also teacher trust. That trust should
come from clear behavior and short language, not from exposing internal score mechanics or inventing
duplicate controls for behavior the teacher already understands.

## Notes

- Keep the main action row calm; `Slumpa` plus the small `Smart` toggle should remain the dominant
  affordance.
- Keep explanation copy compatible with the dedicated `Regler` workspace:
  - compact task-pane summaries may link to `Regler`
  - do not introduce inline rule-editing copy or drawer-first editing affordances here
- Do not add a separate alternate-result button; reruns should stay on the existing `Slumpa`
  action when `Smart` is on.
- Missing-history is a normal first-run state when `Historik` is on by default. Do not teach the
  export-backed checkpoint rule by warning or blocking during `Slumpa`.
- Narrow-search messaging should remain rare and low-drama.

## Planned PR slices

- [PR-0316: ST-27-05 Smart history first-run soft-degrade](../prs/pr-0316-st-27-05-smart-history-first-run-soft-degrade.md)
- [PR-0317: ST-27-03 Smart seating history diversity scoring](../prs/pr-0317-st-27-03-smart-seating-history-diversity-scoring.md)

## 2026-05-11 refinement

Authenticated Smart settings now default `Smart placering` and `Historik` on unless the teacher
opts out. That makes an empty checkpoint window the expected first-run state, not an error.

Resolved behavior:

- keep `Historik` on by default for authenticated teachers
- run Smart seating and Smart grouping without history when no eligible checkpoint exists
- return `used_history=false` for that run and keep normal success feedback
- continue to exclude raw drafts, autosave history, undo/redo, history-drawer drafts, abandoned
  drafts, and public guest local state from Smart history
- keep the existing history-aware solver behavior when eligible export/share checkpoints exist

## 2026-05-12 scorer-diversity refinement

`PR-0317` keeps the no-checkpoint soft-degrade contract from `PR-0316`, but tightens what
`used_history=true` means for seating: accepted share/export checkpoints must now create meaningful
anti-repeat pressure across new seating drafts, with `Håll nära` and `Håll isär` measured by
unordered pair patterns rather than swaps inside the same two seats. This refinement is solver-owned
and does not add teacher-facing score panels or new rerun controls.
