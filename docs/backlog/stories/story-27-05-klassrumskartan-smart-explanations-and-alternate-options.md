---
type: story
id: ST-27-05
title: "Klassrumskartan — Smart explanations and rerun messaging"
status: ready
owners: "agents"
created: 2026-03-25
epic: "EPIC-27"
dependencies: ["ST-27-03", "ST-27-04"]
acceptance_criteria:
  - "Given a teacher has run smart seating or smart grouping, when the result is shown, then the UI presents a short teacher-language explanation rather than raw scores, weights, or debug output."
  - "Given the teacher wants another smart result after a smart run, when `Smart` remains enabled and they use `Slumpa` again, then the UI keeps that same primary action instead of introducing a separate alternate-result button."
  - "Given the teacher reruns smart `Slumpa` but the valid search space is genuinely narrow, when the planner cannot find a materially different strong candidate, then it may show one short teacher-facing message that the current rules leave little room for variation."
  - "Given no eligible checkpoints exist while `Use history` is selected, when the teacher tries to use smart assignment, then the planner blocks that history-enabled run and explains the missing checkpoint requirement briefly instead of silently pretending draft history counts."
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
- Do not add a separate alternate-result button; reruns should stay on the existing `Slumpa`
  action when `Smart` is on.
- Missing-history messaging should teach the export-backed checkpoint rule in plain language.
- Narrow-search messaging should remain rare and low-drama.
