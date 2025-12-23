---
type: story
id: ST-11-23
title: "Tool owner + maintainer permission hardening"
status: done
owners: "agents"
created: 2025-12-23
epic: "EPIC-11"
acceptance_criteria:
  - "Given an accepted suggestion creates a draft tool, then the tool persists an owner_user_id equal to the submitter."
  - "Given an admin manages maintainers, when they attempt to remove the tool owner, then the action is forbidden unless they are superuser."
  - "Given an admin manages maintainers, when they attempt to add/remove a superuser maintainer, then the action is forbidden unless they are superuser."
  - "Given the editor UI lists maintainers, then the owner_user_id is available so the UI can prevent invalid removals."
ui_impact: "Maintainers drawer disables removal for tool owner + superuser rows unless the current user is superuser."
dependencies: ["ST-11-18"]
---

## Context

Maintainers represent edit permissions (“redigeringsbehörigheter”) for a tool. We also need a stable, persisted
definition of the tool’s author/owner (the user who submitted the draft for publication), and stricter rules
around who can change high-privilege edit permissions.

## Policy

- A tool has a single `owner_user_id` (persisted on the tool).
- Admins can add maintainers, but **cannot remove the tool owner** from edit permissions without escalating to
  superuser.
- Only **superusers** can add/remove **superuser** edit permissions.

## Implemented (2025-12-23)

- Added persisted `owner_user_id` to tools (`migrations/versions/0012_tool_owner_user_id.py`,
  `src/skriptoteket/domain/catalog/models.py`, `src/skriptoteket/infrastructure/db/models/tool.py`).
- Backfilled existing tools and ensured owners are included in `tool_maintainers` (migration).
- Enforced permission rules in maintainer handlers (`src/skriptoteket/application/catalog/handlers/assign_maintainer.py`,
  `src/skriptoteket/application/catalog/handlers/remove_maintainer.py`) + unit tests.
- Exposed `owner_user_id` in maintainer list responses (`src/skriptoteket/application/catalog/handlers/list_maintainers.py`,
  `src/skriptoteket/web/api/v1/editor.py`) and updated SPA to disable invalid removals (`MaintainersDrawer.vue`,
  `useToolMaintainers.ts`).
