---
type: story
id: ST-14-01
title: "Admin quick-create draft tool (bypass suggestions)"
status: ready
owners: "agents"
created: 2025-12-25
epic: "EPIC-14"
acceptance_criteria:
  - "Given an admin on /admin/tools, when they create a new tool with a title, then a new unpublished draft tool is created and they are navigated to /admin/tools/{toolId}."
  - "Given the created draft tool, then its slug is set to draft-<tool_id>, owner_user_id is the creating admin, and the admin is added as a maintainer."
  - "Given an admin returns to /admin/tools, then the new tool appears under Pågående with status 'Ingen kod'."
  - "Given the admin tools page, then the create flow does not introduce extra persistent cards that fragment the page (keep the UI unified)."
---

## Context

Admins need a low-friction way to create draft tools for internal iteration, without going through contributor-only
governance hoops intended for non-admins.

This story introduces the quick-create path and uses the v0.1 placeholder slug convention from ADR-0037.

## Notes

- Draft creation should create only the Tool entry (0 versions initially).
- Taxonomy can be empty at creation; publish guards will block publishing until taxonomy is set (ST-14-02).
