---
type: story
id: ST-04-01
title: "Versioned script model (domain + DB + repositories)"
status: done
owners: "agents"
created: 2025-12-14
epic: "EPIC-04"
acceptance_criteria:
  - "Given a tool with no existing versions, when an admin creates a draft version, then a new ToolVersion record is created with state=DRAFT and version_number=1."
  - "Given a draft version exists, when saved again, then a new immutable ToolVersion record is created with incremented version_number."
  - "Given a tool has an active version, when a new version is published, then the old active becomes ARCHIVED and exactly one ACTIVE remains."
  - "Given any version state, when querying tool_versions, then all transitions include actor_id and timestamp for audit."
---

## Context

This story establishes the foundational data model for versioned tool scripts. It creates the `scripting` domain (separate from `catalog`) with `ToolVersion` and `ToolRun` entities, their database representations, and repository implementations.

## Scope

- New domain: `src/skriptoteket/domain/scripting/`
  - `models.py`: ToolVersion (with change_summary and **review_note** fields), ToolRun, VersionState, RunContext, RunStatus
  - Factory functions: `create_draft_version()`, `submit_for_review()`, `publish_version()`
- New protocols: `src/skriptoteket/protocols/scripting.py`
  - `ToolVersionRepositoryProtocol`
  - `ToolRunRepositoryProtocol`
- New infrastructure:
  - `src/skriptoteket/infrastructure/db/models/tool_version.py`
  - `src/skriptoteket/infrastructure/db/models/tool_run.py`
  - `src/skriptoteket/infrastructure/repositories/tool_version_repository.py`
  - `src/skriptoteket/infrastructure/repositories/tool_run_repository.py`
- Migration: `migrations/versions/0005_tool_versions.py`
- Extend Tool: add `active_version_id` FK

## Technical Notes

- Partial unique index enforces single active: `WHERE state = 'active'`
- Unique constraint enforces monotonic uniqueness: `UNIQUE (tool_id, version_number)`
- Version numbers are monotonic per tool (not global)
- `derived_from_version_id` tracks lineage for rollback audit
- `content_hash` (sha256 of "{entrypoint}\\n{source_code}") enables deduplication detection
- `change_summary` field stores human-readable description of changes per version
- `submitted_for_review_by` + `submitted_for_review_at` record the Draft → InReview transition (do not overload reviewer fields)
- `tool_runs.workdir_path` is stored as a relative path/key under the artifacts root (not an absolute host path)
