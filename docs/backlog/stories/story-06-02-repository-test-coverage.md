---
type: story
id: ST-06-02
title: "Improve test coverage for PostgreSQL repositories (tool runs, tools, suggestions)"
status: done
owners: "agents"
created: 2025-12-16
epic: "EPIC-06"
acceptance_criteria:
  - "tool_run_repository.py coverage increases from ~36% to >80%."
  - "tool_repository.py coverage increases from ~66% to >80%."
  - "script_suggestion_repository.py and script_suggestion_decision_repository.py cover update/list edge cases and exceed >80%."
  - "All integration tests pass without schema changes."
---

## Context

Recent coverage reports show several PostgreSQL repository implementations are under-tested, especially around update and
ordering behavior. These repositories are core to admin workflows and execution tracking.

## Scope

- `src/skriptoteket/infrastructure/repositories/tool_run_repository.py`
  - `get_by_id` returns `None` when missing.
  - `create` persists and returns a domain `ToolRun`.
  - `update` updates persisted fields and raises `DomainError(not_found)` when the row is missing.
- `src/skriptoteket/infrastructure/repositories/tool_repository.py`
  - `list_by_tags` returns only published tools and is correctly ordered.
  - `set_published`, `set_active_version_id`, `update_metadata` persist changes.
- `src/skriptoteket/infrastructure/repositories/script_suggestion_repository.py`
  - `update` persists review decisions and raises `DomainError(not_found)` when missing.
  - `list_for_review` ordering is stable (created_at desc, id desc).
- `src/skriptoteket/infrastructure/repositories/script_suggestion_decision_repository.py`
  - `list_for_suggestion` ordering is stable (decided_at desc, id desc).

## Notes

- These should be **integration tests** using the existing testcontainers fixtures (`tests/fixtures/database_fixtures.py`).
- Tests should assert behavior, not SQLAlchemy implementation details.
