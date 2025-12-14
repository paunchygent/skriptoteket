---
type: story
id: ST-04-04
title: "Governance, audit, and rollback (RBAC + publish + history)"
status: ready
owners: "agents"
created: 2025-12-14
epic: "EPIC-04"
acceptance_criteria:
  - "Given I am an Admin, when I publish an InReview version, then it becomes ACTIVE and the previous active becomes ARCHIVED."
  - "Given I am a Contributor, when I try to publish, then I am denied."
  - "Given a publish occurs, when it completes, then the reviewed IN_REVIEW version is archived (publish is copy-on-activate)."
  - "Given any version transition, when it occurs, then actor_id and timestamp are recorded."
  - "Given I am a Superuser, when I rollback to an older version, then a new ACTIVE version is created derived from the old one."
  - "Given I am viewing version history, when I select any version, then I can see its source code and run it in sandbox."
---

## Context

This story implements the governance layer. We follow ADR-0005: Admins manage their tools (publish/depublish), while Superusers handle emergency overrides (rollback).

## Scope

- Application handlers:
  - `PublishVersionHandler` (Admin & Superuser)
  - `RollbackVersionHandler` (Superuser only)
  - `RequestChangesHandler` (Admin & Superuser)
- Domain policy: `src/skriptoteket/domain/scripting/policies.py`
  - Update policies to allow Admin publish.
- Web routes:
  - `POST /admin/tool-versions/{version_id}/publish`
  - `POST /admin/tools/{tool_id}/rollback`

## Permission Matrix

| Action | Contributor | Admin | Superuser |
|--------|-------------|-------|-----------|
| Create draft | Y (own) | Y | Y |
| Submit for review | Y (own) | Y | Y |
| Publish | - | **Y** | Y |
| Rollback | - | - | **Y** |

## Rollback Flow

1. Superuser selects archived version to restore
2. System creates NEW version with:
   - `version_number` = next in sequence
   - `state` = ACTIVE
   - `source_code` = copied from archived
   - `derived_from_version_id` = archived version's ID
   - `published_by` = superuser
3. Previous ACTIVE → ARCHIVED
4. `tools.active_version_id` updated

## Technical Notes

- Audit trail is append-only (no version deletion)
- All transitions logged with actor + timestamp
- Future: emit domain events for external audit systems
