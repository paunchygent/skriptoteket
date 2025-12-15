---
type: adr
id: ADR-0014
title: "Append-only tool versions with single active version per tool"
status: proposed
owners: "agents"
deciders: ["user-lead"]
created: 2025-12-14
updated: 2025-12-15
---

## Context

Tools need draft testing, approval workflows, and exactly one published version at a time. Published snapshots must be immutable and auditable. We need a versioning model that supports:

- Draft iteration and sandbox testing
- Review workflow before publishing
- Clear audit trail of who published what and when
- Rollback to previous versions
- Future export to GitHub as canonical history

## Decision

### Version lifecycle states

```text
Draft → InReview → Active → Archived
```

- **DRAFT**: Editable by author/admin; can be run in sandbox
- **IN_REVIEW**: Frozen; reviewers can run it; no edits (must create new draft)
- **ACTIVE**: User-visible runnable version; exactly one per tool
- **ARCHIVED**: Historical; viewable; runnable only by admins (optional)

### Append-only versioning

- Each explicit "Save" creates a new immutable version (append-only)
- Every saved snapshot is addressable and auditable
- Version numbers are monotonic integers per tool (v1, v2, v3...)

### Single active version

- `tools.active_version_id` points to the one ACTIVE `tool_versions` record
- Database constraint (partial unique index) prevents multiple ACTIVE per tool:

  ```sql
  CREATE UNIQUE INDEX ON tool_versions(tool_id) WHERE state = 'active';
  ```

### Copy-on-activate publishing

When publishing (InReview → Active):

1. Archive the current ACTIVE version (if any)
2. Create a NEW version record with state=ACTIVE, copying content from the reviewed version
3. New version gets next version_number (e.g., v12 InReview → v13 Active)
4. Update `tools.active_version_id` to point to new version
5. Archive the reviewed IN_REVIEW version (it is "consumed" by publishing)

Rollback works the same way: publish a new ACTIVE derived from an older ARCHIVED version.

Rationale for copy-on-activate over pointer-switching:

- Clean "published timeline" (each publish event is a distinct record)
- Makes GitHub export straightforward: each published version maps to a single content snapshot
- Audit trail reads naturally: "Rolled back by creating v17 from v12"

## Consequences

- Clear, linear publish history for audit and compliance
- Version history grows with saves (acceptable for on-prem scale)
- "Load old version for testing" is trivial (select version, run sandbox)
- Export-to-GitHub is a deterministic transformation
- Rollback is safe and auditable (creates new record, does not mutate history)

## Implementation status (as of 2025-12-15)

### Done

- Domain function exists: `src/skriptoteket/domain/scripting/models.py` (`publish_version()` implements copy-on-activate).
- DB support exists: `migrations/versions/0005_tool_versions.py` (states + single-ACTIVE constraint + `tools.active_version_id` FK).
- Application + DI prerequisites exist:
  - `src/skriptoteket/application/scripting/commands.py` (`PublishVersionCommand/Result`)
  - `src/skriptoteket/protocols/scripting.py` (`PublishVersionHandlerProtocol`)
  - `src/skriptoteket/di.py` (Dishka binding for `PublishVersionHandlerProtocol`)
- Application handler exists:
  - `src/skriptoteket/application/scripting/handlers/publish_version.py`
- Web route exists:
  - `src/skriptoteket/web/pages/admin_scripting.py` (`POST /admin/tool-versions/{version_id}/publish`)
- Admin UI decision section exists:
  - `src/skriptoteket/web/templates/admin/script_editor.html`
- Repo support exists for persisting `tools.active_version_id` updates:
  - `src/skriptoteket/protocols/catalog.py` (`ToolRepositoryProtocol.set_active_version_id`)
  - `src/skriptoteket/infrastructure/repositories/tool_repository.py`
- Tests cover publish behavior:
  - `tests/unit/application/test_scripting_review_handlers.py`
  - `tests/integration/web/test_admin_scripting_review_routes.py`

### Pending

- Operational behavior tracking (story): `docs/backlog/stories/story-04-04-governance-audit-rollback.md` (ST-04-04).
- Rollback wiring (Superuser-only): create new ACTIVE derived from an ARCHIVED version (same copy-on-activate rules).
