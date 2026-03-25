---
type: story
id: ST-27-05
title: "Klassrumskartan — Smart explanations and alternate options"
status: ready
owners: "agents"
created: 2026-03-25
epic: "EPIC-27"
dependencies: ["ST-27-03", "ST-27-04"]
acceptance_criteria:
  - "Given a teacher has run smart seating or smart grouping, when the result is shown, then the UI presents a short teacher-language explanation rather than raw scores, weights, or debug output."
  - "Given the teacher wants another result after a smart run, when follow-up actions are shown, then one low-emphasis action such as `En smart variant till` is available without adding a second competing main button to the toolbar."
  - "Given the teacher asks for `En smart variant till`, when the planner can find a materially different valid result, then it returns a distinct assignment rather than repeating the same assignment hash."
  - "Given the teacher asks for `En smart variant till` but no materially different valid result is available, when the planner responds, then it shows a short teacher-facing no-further-variant message rather than silently repeating the same result."
  - "Given no eligible checkpoints exist while `Use history` is selected, when the teacher tries to use smart assignment, then the planner blocks that history-enabled run and explains the missing checkpoint requirement briefly instead of silently pretending draft history counts."
  - "Given the solver cannot satisfy every rule, when the best available result is shown, then the teacher sees one short best-effort message and not a solver-jargon error surface."
ui_impact: "Yes (teacher-language explanation and follow-up affordances)"
data_impact: "No"
---

## Context

The product goal is not only stronger assignment quality but also teacher trust. That trust should
come from clear behavior and short language, not from exposing internal score mechanics.

## Notes

- Keep the main action row calm; `Slumpa` plus the small `Smart` toggle should remain the dominant
  affordance.
- `En smart variant till` belongs after a smart result, not as another primary toolbar button.
- Missing-history messaging should teach the export-backed checkpoint rule in plain language.
