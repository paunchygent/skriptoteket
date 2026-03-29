---
type: story
id: ST-30-02
title: "Adopt transition continuity across editor and selector shells"
status: done
owners: "agents"
created: 2026-03-29
epic: "EPIC-30"
dependencies:
  - "ST-30-01"
acceptance_criteria:
  - "Given the code editor switches between `Källkod`, `Diff`, `Metadata`, and `Testkör`, when this story ships, then the editor keeps its stable shell and uses a retained-surface overlap transition instead of a visible teardown/rebuild swap."
  - "Given the rules map, tool file picker, and Vault panel each keep one persistent local shell while their main body changes, when this story ships, then those selector-driven surfaces preserve continuity instead of flashing to blank or abrupt body replacement."
  - "Given the SPA still contains older `out-in` transitions outside the main selector-shell scope, when this story is implemented, then those surfaces are explicitly audited and only the ones that still create visible continuity problems are changed."
  - "Given this is a UI/route-affecting slice, when implementation is verified, then focused frontend tests, live browser proof, and `.agents/handoff.md` are updated."
ui_impact: "Yes (editor, planner rules map, tool-run file picker, Vault, and transition audit surfaces)"
data_impact: "No"
---

## Context

`ST-30-01` established the continuity rule and inventory. This story applies that rule to the
remaining qualifying selector shells and audits the adjacent `out-in` surfaces so the app stops
mixing continuity patterns.

## Notes

- The editor workspace selector is the highest-value adoption target and should lead this slice.
- The smaller selector shells should use the same continuity rule without over-engineering loading
  state that they do not need.

## Planned PR slices

- [PR-0166: ST-30-02 transition continuity adoption and remaining transition audit](../prs/pr-0166-st-30-02-transition-continuity-adoption-and-remaining-transition-audit.md)

## References

- Epic parent: [EPIC-30](../epics/epic-30-frontend-transition-continuity-for-same-shell-selectors.md)
- Transition ADR: [ADR-0077](../../adr/adr-0077-same-shell-transition-continuity.md)
- Transition reference: [REF-frontend-transition-continuity-v1](../../reference/ref-frontend-transition-continuity-v1.md)
