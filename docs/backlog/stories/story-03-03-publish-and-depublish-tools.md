---
type: story
id: ST-03-03
title: "Admins publish/depublish tools (catalog visibility)"
status: done
owners: "agents"
created: 2025-12-13
epic: "EPIC-03"
dependencies:
  - "ST-04-01 (tools.active_version_id + ToolVersion ACTIVE)"
acceptance_criteria:
  - "Given I am an admin and a tool has an ACTIVE script version, when I publish the tool, then it becomes visible in browse and runnable for users."
  - "Given I am an admin and a tool is published, when I depublish the tool, then it is hidden from browse and `GET /tools/{slug}/run` returns 404."
  - "Given I am an admin and a tool has no ACTIVE script version, when I attempt to publish the tool, then the request is rejected and the tool remains unpublished."
  - "Given a tool is depublished, when it is hidden, then tool versions and prior run records remain stored for audit/debugging."
---

## Context

This story governs **catalog visibility** (`tools.is_published`). It is distinct from **script version publishing**
(ToolVersion state transitions and `tools.active_version_id`), which is handled in EPIC-04.

## Notes

- Recommendation: enforce "published implies runnable" by requiring `active_version_id != null` when publishing.
- Depublishing should be non-destructive: it hides the tool from end-users without deleting versions or runs.
