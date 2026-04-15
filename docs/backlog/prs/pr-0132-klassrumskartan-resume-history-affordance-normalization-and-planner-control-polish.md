---
type: pr
id: PR-0132
title: "Klassrumskartan: resume/history affordance normalization and planner control polish"
status: done
owners: "agents"
created: 2026-03-24
updated: 2026-04-01
stories:
  - "ST-29-04"
tags: ["frontend", "ux", "klassrumskartan", "affordances", "playwright"]
dependencies:
  - "PR-0111"
  - "PR-0131"
acceptance_criteria:
  - "Resume cards and history surfaces use the same planner control language as the rest of Klassrumskartan."
  - "Ad hoc destructive cues are replaced with typed destructive affordances that feel product-level rather than prototype-level."
  - "A focused browser proof verifies the normalized affordances on the live local SPA."
---

## Problem

After overview button hierarchy is corrected, the remaining affordance inconsistency becomes more
obvious in resumable cards and history surfaces. Secondary settings actions and destructive controls
still feel less settled than the rest of the planner.

## Goal

Normalize resume/history controls so the planner presents a more consistent control language across
overview and continuity surfaces.

## Locked design decisions

- Build on the hierarchy work from `PR-0131` rather than inventing a second visual language.
- Replace ad hoc destructive cues with typed planner affordances.
- Keep resumable-card functionality intact; this is not a workflow redesign.
- Validate the polish pass with real browser proof on the local SPA.

## Non-goals

- No new continuity/history capabilities.
- No changes to unfinished teacher-note semantics.
- No redesign of the top overview composition.

## Implementation plan

- Normalize secondary controls in the overview resumable cards.
- Replace ad hoc destructive cues in history/resume surfaces with the planner's standard destructive
  affordance model.
- Tighten any inconsistent icon/text treatments that still make these surfaces feel unlike the rest
  of the planner.
- Add focused browser proof for the final affordance pass.

## Proposed module focus

- `frontend/apps/skriptoteket/src/views/apps/components/PlannerOverviewResumeCards.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerHistoryDrawer.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerToolbarIconButton.vue`

## Test plan

- Focused frontend tests for resume/history secondary and destructive controls.
- Manual browser verification on the local SPA confirming the planner control language feels
  consistent across overview and history surfaces.

## Rollback plan

- Restore the current resume/history control treatments while keeping the overview hierarchy changes
  from `PR-0131`.

## References

- Story parent: [ST-29-04](../stories/story-29-04-klassrumskartan-overview-hierarchy-and-class-first-dashboard-redesign.md)
- Resume baseline: [PR-0111](pr-0111-klassrumskartan-overview-resumable-cta-and-workspace-entry-polish.md)
- Overview hierarchy baseline: [PR-0131](pr-0131-klassrumskartan-overview-button-hierarchy-and-destructive-action-de-emphasis.md)
- Frontend skill: [integrated-frontend-stack](/Users/olofs_mba/Documents/Repos/skill-repository/skills/integrated-frontend-stack/SKILL.md)
- Browser automation skill: [playwright-testing](../../..//Users/olofs_mba/.codex/skills/playwright-testing/SKILL.md)
- Design-system rule: [045-huleedu-design-system](../../../.codex/rules/045-huleedu-design-system.md)
- Browser automation rule: [075-browser-automation](../../../.codex/rules/075-browser-automation.md)
