---
type: story
id: ST-30-01
title: "Frontend transition continuity inventory and canonical adoption plan"
status: ready
owners: "agents"
created: 2026-03-29
epic: "EPIC-30"
dependencies:
  - "ST-29-02"
acceptance_criteria:
  - "Given Skriptoteket now has a working planner-shell continuity fix, when this story is reviewed, then `ADR-0077` and `REF-frontend-transition-continuity-v1` define the retained-surface overlap-crossfade pattern as the canonical same-shell selector transition method and explicitly forbid blank `out-in` handoffs."
  - "Given the app contains several selector-driven shells, when this story is completed, then the repo documents an inventory of all currently known same-route or same-shell selector/rail transitions, their owning files, and their adoption priority."
  - "Given the team needs a paced rollout, when this story is completed, then the next concrete adoption target is explicitly named as the code editor workspace selector and smaller selector surfaces are sequenced behind it."
  - "Given future frontend work should discover this rule quickly, when this story is completed, then the design-system codemap and related doctrine references point to the continuity standard."
ui_impact: "Yes (docs governing future planner/editor and selector transitions)"
data_impact: "No"
---

## Context

The planner shell fix now demonstrates the transition behavior Skriptoteket should standardize:
the current workspace remains coherent until the next one is actually ready, and the user sees a
short crossfade rather than a visible teardown/rebuild cycle.

Without a shared inventory and doctrine, that learning will stay local to Klassrumskartan and the
same transition bug will be reintroduced elsewhere.

## Notes

- This story is intentionally planning and doctrine first; it does not itself perform the editor
  adoption.
- The inventory should stay pragmatic: dense workspace shells first, smaller selector cards later.

## Planned PR slices

- [PR-0165: ST-30-01 transition continuity decision, inventory, and adoption plan](../prs/pr-0165-st-30-01-transition-continuity-decision-inventory-and-adoption-plan.md)

## References

- Epic parent: [EPIC-30](../epics/epic-30-frontend-transition-continuity-for-same-shell-selectors.md)
- Transition ADR: [ADR-0077](../../adr/adr-0077-same-shell-transition-continuity.md)
- Transition reference: [REF-frontend-transition-continuity-v1](../../reference/ref-frontend-transition-continuity-v1.md)
- Planner workspace doctrine: [REF-klassrumskartan-workspace-ui-doctrine-2026-03-28](../../reference/ref-klassrumskartan-workspace-ui-doctrine-2026-03-28.md)
- Frontend codemap: [REF-frontend-design-system-codemap-2026-03-28](../../reference/ref-frontend-design-system-codemap-2026-03-28.md)
