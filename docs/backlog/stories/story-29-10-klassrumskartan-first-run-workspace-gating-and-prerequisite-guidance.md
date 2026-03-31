---
type: story
id: ST-29-10
title: "Klassrumskartan — First-run workspace gating and prerequisite guidance"
status: ready
owners: "agents"
created: 2026-03-31
updated: 2026-03-31
epic: "EPIC-29"
dependencies:
  - "ST-24-07"
  - "ST-27-07"
  - "ST-29-02"
acceptance_criteria:
  - "Given no class is selected or available, when Klassrumskartan opens in `Översikt`, then only `Översikt` is available, `Grupper`, `Sittplatser`, and `Regler` are visibly disabled and non-clickable, the overview guidance reads exactly `Börja med att skapa en klasslista.`, and the disabled workspace hint reads exactly `Skapa först en klasslista.`"
  - "Given a class is selected but no classroom is selected or available, when the planner selector renders in `Översikt` or the live planner shell, then `Grupper` and `Regler` remain available, `Sittplatser` is visibly disabled and non-clickable, the overview guidance reads exactly `Nu har du skapat din klass. Skapa eller välj ett klassrum för att använda Sittplatser.`, and the disabled seating hint reads exactly `Skapa eller välj först ett klassrum.`"
  - "Given the prerequisite guidance surface is shown, when the teacher wants more help, then the supporting help line reads exactly `Behöver du mer vägledning kan du trycka på Hjälp.` and no toast, modal, guided walkthrough, or animated onboarding surface is introduced in this slice."
  - "Given browser proof is run at the `EPIC-29` `laptop` (`1366x768`) and `desktop` (`1440x900`) review viewports, when the first-run and class-without-classroom states are checked, then unavailable workspaces are obvious at a glance and no workspace option falls through to a silent click path."
ui_impact: "Yes (workspace selector gating and compact overview guidance)"
data_impact: "No"
---

## Context

Klassrumskartan currently presents `Grupper`, `Sittplatser`, and `Regler` as if they are always
available, but new teachers can still land in prerequisite states where those workspaces should not
be entered yet. Today that produces the wrong UX failure: the controls look active, the teacher
clicks them, and the app quietly does nothing.

This story fixes the first-run reachability language without turning the planner into a larger
onboarding feature. The scope is explicit affordance truthfulness plus approved Swedish copy.

## Notes

- `Regler` stays available as soon as a class exists; this story does **not** add a classroom
  prerequisite for `Regler`.
- The exact approved copy above is locked for implementation unless a later planning update changes
  it explicitly.
- The guidance must live in the existing compact planner surface; do not add a large banner,
  modal, toast, walkthrough, or animation-led onboarding layer here.
- `ST-08-34` and the existing help drawer remain the follow-on guidance path; this story only adds
  the small in-context pointer to `Hjälp`.

## Planned PR slices

- [PR-0184: ST-29-10 canonical mockup folder and first-run preview](../prs/pr-0184-st-29-10-canonical-mockup-folder-and-first-run-preview.md)
- [PR-0182: ST-29-10 workspace selector reachability and locked disabled-state copy](../prs/pr-0182-st-29-10-workspace-selector-reachability-and-locked-disabled-state-copy.md)
- [PR-0183: ST-29-10 overview prerequisite guidance and help-affordance copy](../prs/pr-0183-st-29-10-overview-prerequisite-guidance-and-help-affordance-copy.md)

## References

- Epic parent: [EPIC-29](../epics/epic-29-klassrumskartan-desktop-first-workspace-overhaul.md)
- Overview-first baseline: [ST-24-07](story-24-07-group-seating-studio-overview-first-workspace-management.md)
- Rules-workspace baseline: [ST-27-07](story-27-07-klassrumskartan-rules-workspace-and-dual-map-authoring.md)
- Workspace doctrine: [REF-klassrumskartan-workspace-ui-doctrine-2026-03-28](../../reference/ref-klassrumskartan-workspace-ui-doctrine-2026-03-28.md)
- Planner contextual help baseline: [ST-08-34](story-08-34-klassrumskartan-contextual-help.md)
