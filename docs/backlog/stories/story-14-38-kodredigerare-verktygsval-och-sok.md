---
type: story
id: ST-14-38
title: "Kodredigerare: tool picking, search, and navigation"
status: in_progress
owners: "agents"
created: 2026-01-26
epic: "EPIC-14"
ui_impact: "Yes (new /editor hub + editor tool menu)"
data_impact: "No (localStorage only)"
acceptance_criteria:
  - "Given a contributor has at least one editable tool, when navigating to /editor, then the app automatically opens the most recently opened editor tool if available."
  - "Given a contributor navigates to /editor?pick=1, when the page loads, then it shows a compact tool picker with sections for 'Senast öppnade' and 'Mina verktyg'."
  - "Given a user searches in /editor?pick=1, when entering a query, then the UI shows a dropdown/popover with at most 5 best matches across all tools the user can edit."
  - "Given a user searches in the editor 'Verktyg' dropdown, when entering a query, then it searches across all tools the user can edit and returns at most 5 best matches."
  - "Given there are more matches than the first 5, when searching, then the UI shows 'Visar 5 av N' and (admin only) offers a link to 'Visa alla verktyg' without hiding results."
  - "Given the user opens the editor toolbar, when viewing menus, then 'Spara/Öppna' is positioned to the left of 'Verktyg'."
  - "Given the home dashboard and sidebar navigation, when viewing labels, then 'Kodredigerare' (indefinite) is used in navigation and 'Kodredigeraren' (definite) is used as the hub heading."
---

## Context

Tool authoring needs a cohesive way to switch, search, and create tools without falling back to clunky legacy lists.

## Notes

- “Alla verktyg” means “all tools the user is allowed to edit (role/flags)”. For now, admin uses `/api/v1/admin/tools`,
  contributors use `/api/v1/my-tools`.
- Keep the picker UI compact and aligned with the tool editor’s design language (Brutalist Academic + tokens-first).
