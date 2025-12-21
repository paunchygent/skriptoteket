---
type: epic
id: EPIC-03
title: "Tool governance workflow (suggest → review → publish/depublish)"
status: done
owners: "agents"
created: 2025-12-13
outcome: "Contributors can suggest tools and admins can review decisions and manage tool publish/depublish without ad-hoc processes."
---

## Scope

- Contributor suggestion submission.
- Admin review queue and decisioning (accept/modify/deny).
- Tool publish/depublish lifecycle controls (catalog visibility).

Note: publishing script *versions* (ToolVersion state transitions + runner execution) is handled in EPIC-04.

## Dependencies

- EPIC-02 (identity and RBAC).
- EPIC-04 (dynamic tool scripts), if enforcing \"published implies runnable\" via `tools.active_version_id`.
- ADR-0005 (role hierarchy) and ADR-0006 (identity/authorization).
