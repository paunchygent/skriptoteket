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
- Script version lifecycle exists end-to-end for draft + submit-for-review + sandbox + publish + request-changes.
- Application DTOs exist (publish + request-changes):
  - `src/skriptoteket/application/scripting/commands.py`
- Protocols + DI wiring exists:
  - `src/skriptoteket/protocols/scripting.py`
  - `src/skriptoteket/di.py`
- Repo support exists for persisting `tools.active_version_id`:
  - `src/skriptoteket/protocols/catalog.py`
  - `src/skriptoteket/infrastructure/repositories/tool_repository.py`
- Application handlers exist (publish + request-changes):
  - `src/skriptoteket/application/scripting/handlers/publish_version.py`
  - `src/skriptoteket/application/scripting/handlers/request_changes.py`
- Web endpoints exist:
  - `src/skriptoteket/web/pages/admin_scripting.py` (`POST /admin/tool-versions/{version_id}/publish`)
  - `src/skriptoteket/web/pages/admin_scripting.py` (`POST /admin/tool-versions/{version_id}/request-changes`)
- Editor review UI exists (admin/superuser only for `IN_REVIEW`):
  - `src/skriptoteket/web/templates/admin/script_editor.html`
- Admin-skripteditor har konsekvent svensk UI-copy (inkl. state-labels och körningsresultat).
- Katalog-metadata är separat från skriptets källkod (admin kan uppdatera titel/sammanfattning i editorn):
  - `POST /admin/tools/{tool_id}/metadata`
- Tests exist:
  - `tests/unit/application/test_scripting_review_handlers.py`
  - `tests/integration/web/test_admin_scripting_review_routes.py`
  - `tests/integration/web/test_admin_tool_metadata_routes.py` (regression: Katalog summary is tool metadata)

### Missing (validated gaps)

- Rollback workflow is still missing (Superuser-only): handler + route + UI (out of scope for this session).

### Implementation notes

- Mirrors the suggestions decision pattern (ST-03-02): command/handler/protocol + admin-only POST + conditional editor card.
- Persists publish outcome by: archiving reviewed/previous-active, creating NEW ACTIVE, updating `tools.active_version_id` (same UoW).

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
