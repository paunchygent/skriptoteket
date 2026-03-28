---
type: story
id: ST-29-07
title: "Klassrumskartan — Reduced mobile companion layouts and breakpoint cutover"
status: ready
owners: "agents"
created: 2026-03-28
epic: "EPIC-29"
dependencies:
  - "ST-29-04"
  - "ST-29-05"
  - "ST-29-06"
acceptance_criteria:
  - "Given the viewport is at the `EPIC-29` `phone` (`390x844`) or `tablet` (`768x1024`) review viewport rather than the `laptop` or `desktop` desktop-proof widths, when the responsive cutover activates, then mobile and narrow-tablet layouts intentionally reduce simultaneous panels and secondary controls instead of preserving the full desktop composition as stacked cards."
  - "Given a planner operation is not realistically usable on phone portrait layouts, when the reduced mobile companion experience ships, then that operation may be deferred, hidden, or rerouted instead of being forced into false feature parity."
  - "Given the desktop redesign is already in place, when smaller-screen layouts render, then they do not reintroduce the earlier mobile-first compromises back into laptop widths."
  - "Given browser proof is run across the `EPIC-29` `phone` (`390x844`), `tablet` (`768x1024`), `laptop` (`1366x768`), and `desktop` (`1440x900`) review viewports, when this story is reviewed, then the breakpoint behavior follows the explicit desktop-first policy from the workspace doctrine."
ui_impact: "Yes (responsive cutover and reduced mobile companion layouts)"
data_impact: "No"
---

## Context

The redesign should not solve mobile by asking desktop to become smaller, slower, or more stacked.
This story defines the responsive cutover after the desktop workspace has already been settled.

## Notes

- This is intentionally last in the sequence.
- The goal is not parity. The goal is a credible smaller-screen companion experience that protects
  the desktop product.

## References

- Epic parent: [EPIC-29](../epics/epic-29-klassrumskartan-desktop-first-workspace-overhaul.md)
- Workspace doctrine: [REF-klassrumskartan-workspace-ui-doctrine-2026-03-28](../../reference/ref-klassrumskartan-workspace-ui-doctrine-2026-03-28.md)
- Responsive baseline ADR: [ADR-0020](../../adr/adr-0020-responsive-mobile-adaptation.md)
