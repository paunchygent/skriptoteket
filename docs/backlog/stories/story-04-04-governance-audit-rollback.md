---
type: story
id: ST-04-04
title: "Governance, audit, and rollback (RBAC + publish + history)"
status: ready
owners: "agents"
created: 2025-12-14
updated: 2025-12-15
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
  - `POST /admin/tool-versions/{version_id}/request-changes`
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
- Publishing/rollback MUST update `tools.active_version_id` to the newly created ACTIVE version.
  - If `tools.is_published == true`, end-users immediately run the new ACTIVE version (see ST-03-03 invariant).
  - If the tool is depublished, it remains hidden even though a new ACTIVE exists.

## Implementation status (as of 2025-12-15)

### Done

- Domain copy-on-activate publish exists: `src/skriptoteket/domain/scripting/models.py` (`publish_version()`).
- Script version lifecycle exists end-to-end for draft + submit-for-review + sandbox (ST-04-03), but without publish/decision wiring.

### Missing (validated gaps)

- No application command/result for publishing a version: `src/skriptoteket/application/scripting/commands.py`
- No application handler module: `src/skriptoteket/application/scripting/handlers/`
- No handler protocol + DI wiring: `src/skriptoteket/protocols/scripting.py`, `src/skriptoteket/di.py`
- No web endpoint: `src/skriptoteket/web/pages/admin_scripting.py` (`POST /admin/tool-versions/{version_id}/publish`)
- No admin UI section in editor: `src/skriptoteket/web/templates/admin/script_editor.html`
- Additional required plumbing: update `tools.active_version_id` on publish (currently no repo/protocol method to persist it).
- Reject/request-changes workflow is not implemented in domain/application/web yet (needs decision on semantics + reviewer rationale storage).

### Planned approach

- Mirror the suggestions decision pattern (ST-03-02):
  - `PublishVersionCommand` / `PublishVersionHandler` / `PublishVersionHandlerProtocol`
  - Admin-only route `POST /admin/tool-versions/{version_id}/publish`
  - Conditional decision card in `admin/script_editor.html` shown only for `IN_REVIEW` + admin/superuser
- Persist publish outcome by:
  - creating the new ACTIVE version row,
  - archiving the reviewed version (and previous active if any),
  - updating `tools.active_version_id` in the same Unit of Work transaction.

### Request changes (clarified)

`RequestChangesHandler` is the “InReview → Draft” workflow step. Recommended behavior:

1. Precondition: the target version is `state=in_review`.
2. Transition the in-review version out of publishable state (recommended: set `state=archived` and set
   `reviewed_by_user_id`/`reviewed_at`).
3. Create a NEW draft version (append-only) derived from the reviewed version:
   - `state=draft`
   - `version_number=next`
   - copy `source_code`/`entrypoint`
   - `derived_from_version_id = in_review.id`
   - `created_by_user_id = in_review.created_by_user_id` (preserves contributor ownership rules)
   - store the request message in `change_summary` (until a dedicated reviewer-note field exists)
- Future: emit domain events for external audit systems
