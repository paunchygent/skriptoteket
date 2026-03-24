---
type: story
id: ST-26-08
title: "Klassrumskartan — Overview action hierarchy and affordance polish"
status: ready
owners: "agents"
created: 2026-03-24
epic: "EPIC-26"
dependencies:
  - "EPIC-24"
  - "ST-24-07"
  - "ST-26-07"
acceptance_criteria:
  - "Given the teacher is in `Oversikt`, when class and classroom management actions render, then create is the clear primary action while edit and delete read as lighter secondary and destructive affordances rather than equal-weight siblings."
  - "Given resumable overview surfaces and history controls remain in the planner, when secondary controls are shown, then they use a consistent planner button language instead of one-off symbols or ad hoc destructive cues."
  - "Given this polish slice ships, when compared with the editor's button hierarchy and affordance discipline, then the planner reads as more deliberate without changing the approved desktop-first overview layout."
  - "Given the planner's teacher-note semantics are still provisional, when this story is implemented, then it does not finalize or broaden that unfinished settings model under the guise of UI polish."
ui_impact: "Yes (overview actions + planner affordances)"
data_impact: "No"
---

## Context

`ST-24-07` and its follow-up PRs made `Oversikt` genuinely usable, but several actions still read as
prototype-weight controls:

- create, edit, and delete often look like equal-weight siblings
- some planner surfaces still mix polished controls with one-off icon/symbol affordances
- destructive actions are not always visually separated from routine management actions

This is a hierarchy and affordance pass, not a change in planner direction.

## Problem

The planner now has enough capability that weak button hierarchy stands out more:

- primary actions are not always obvious at a glance
- secondary actions take more visual weight than they need
- destructive actions can feel too casual or too prominent depending on the surface
- resume/history controls do not yet feel fully normalized with the rest of the planner UI

Compared with the editor, the planner still feels less settled at the control-language level.

## Decisions

- Keep the approved overview card composition and desktop symmetry.
- Make create the strongest call-to-action in overview management panels.
- Demote edit to a lighter secondary treatment.
- Keep delete explicit but visually de-emphasized relative to create.
- Normalize planner secondary controls around shared affordances rather than one-off glyphs or
  emoji-like destructive cues.
- Do not finalize teacher-note semantics or smart-placement terminology in this story.

## Notes

- This story is intentionally a polish slice after layout and toolbar structure have stabilized.
- The goal is better scanability and trust, not more UI density.

## Recommended decomposition

### PR-0131

Focus:

- rebalance overview management actions in the class and classroom panels
- make create the dominant CTA
- demote edit and delete to clearer secondary/destructive treatments
- keep the current compact overview layout intact

### PR-0132

Focus:

- normalize resumable-card secondary controls
- remove ad hoc destructive cues in history/resume surfaces
- align planner secondary-control language with the rest of the planner after `PR-0131`
- add browser proof for the polished control hierarchy

## References

- Epic parent: [EPIC-26](../epics/epic-26-klassrumskartan-explicit-exports-and-class-list-import.md)
- Overview-first baseline: [ST-24-07](story-24-07-group-seating-studio-overview-first-workspace-management.md)
- Toolbar-structure prerequisite: [ST-26-07](story-26-07-klassrumskartan-stable-task-toolbars-and-action-zoning.md)
- Overview management baseline: [PR-0110](../prs/pr-0110-klassrumskartan-overview-compact-class-and-classroom-management.md)
- Overview resume baseline: [PR-0111](../prs/pr-0111-klassrumskartan-overview-resumable-cta-and-workspace-entry-polish.md)
- Overview simplification baseline: [PR-0112](../prs/pr-0112-klassrumskartan-overview-design-simplification-and-seamless-workspace-transitions.md)
- Frontend skill: [skriptoteket-frontend-specialist](../../../.claude/skills/skriptoteket-frontend-specialist/SKILL.md)
- Browser automation skill: [playwright-testing](../../../.claude/skills/playwright-testing/SKILL.md)
- Design-system rule: [045-huleedu-design-system](../../../.agents/rules/045-huleedu-design-system.md)
- Sprint-planning workflow: [ref-sprint-planning-workflow](../../reference/ref-sprint-planning-workflow.md)
