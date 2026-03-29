---
type: story
id: ST-08-34
title: "Klassrumskartan contextual help (overview + workspace modes)"
status: done
owners: "agents"
created: 2026-03-29
epic: "EPIC-08"
dependencies:
  - "ST-11-19"
  - "ST-29-02"
acceptance_criteria:
  - "Given a teacher opens `Hjälp` in Klassrumskartan `Översikt`, when the panel opens, then it shows planner-specific overview help instead of generic app help or a blank body."
  - "Given a teacher opens `Hjälp` in `Grupper`, `Sittplatser`, or `Regler`, when the planner workspace mode changes, then the active help topic updates to the matching planner section without manual topic selection."
  - "Given the planner help copy is sourced from the getting-started guide, when the generated help module is rebuilt, then the rendered planner help stays aligned with the guide and excludes video-only annotations."
ui_impact: "Yes (planner help panel content and planner-mode context wiring)"
data_impact: "No"
---

## Context

Klassrumskartan now has a planner-specific getting-started guide, but the SPA help framework only covered
route-level topics. The planner itself is a multi-mode surface inside one app route, so the help panel
needs mode-aware context (`Översikt`, `Grupper`, `Sittplatser`, `Regler`) rather than a single
`apps_detail` topic.

## Scope

- Add planner-specific help topic ids and context-first help resolution for Klassrumskartan modes.
- Generate planner help content from the canonical guide document instead of hardcoding duplicated copy.
- Render the generated planner section in the shared help panel.
- Cover the overview render path and context switching with focused frontend tests.

## Notes

- The guide file under `docs/guides/` is the source of truth for planner help copy.
- Planner help is contextual inside the existing global help panel; this story does not add a second
  planner-only help surface.
- `Grupper`, `Sittplatser`, and `Regler` still depend on planner reachability rules (for example,
  selected roster), but once those views are mounted the help topic should follow the active mode.

## Files

- `docs/guides/guide-klassrumskartan-kom-igang.md`
- `scripts/generate_planner_help.py`
- `frontend/apps/skriptoteket/src/components/help/useHelp.ts`
- `frontend/apps/skriptoteket/src/components/help/helpTopics.ts`
- `frontend/apps/skriptoteket/src/components/help/HelpPanel.vue`
- `frontend/apps/skriptoteket/src/components/help/topics/HelpTopicPlanner.vue`
- `frontend/apps/skriptoteket/src/components/help/plannerHelpSections.generated.ts`
- `frontend/apps/skriptoteket/src/components/help/HelpPanel.spec.ts`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerClassWorkspace.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerWorkspaceShell.vue`
