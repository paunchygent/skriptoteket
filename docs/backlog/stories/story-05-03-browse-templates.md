---
type: story
id: ST-05-03
title: "Browse template migration"
status: done
owners: "agents"
created: 2025-12-15
epic: "EPIC-05"
acceptance_criteria:
  - "Given the browse page loads, when hovering a list item, then background highlights with navy-02"
  - "Given a list item is hovered, when viewing the arrow, then it turns burgundy"
---

## Context

Migrating the public catalog browsing pages to the new design system.

## Tasks

- Convert `browse_professions.html` to use HuleEdu list/row classes
- Convert `browse_categories.html` to use HuleEdu list/row classes
- Convert `browse_tools.html` to use HuleEdu list/row classes
- Add arrow indicators to navigation links
