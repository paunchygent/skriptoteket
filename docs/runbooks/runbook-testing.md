---
type: runbook
id: RUN-testing
title: "Runbook: Testing (Pytest + Vitest + Playwright)"
status: active
owners: "agents"
created: 2025-12-29
updated: 2025-12-29
system: "skriptoteket-dev"
---

This runbook describes how to run tests locally (and what each suite is responsible for).

## Quick start

```bash
# Backend checks
pdm run lint
pdm run typecheck
pdm run test

# Frontend checks
pdm run fe-type-check
pdm run fe-lint
pdm run fe-test

# UI smoke (Playwright)
pdm run ui-smoke
pdm run ui-editor-smoke
pdm run ui-runtime-smoke
```

## Backend (Pytest)

### When to use

- Unit tests: domain/application behavior with mocked protocols.
- Integration tests: repositories/migrations and other Docker-backed dependencies.

### Commands

```bash
pdm run test
```

### Notes

- Integration tests use Docker (testcontainers). Ensure Docker Desktop is running and accessible.
- Migration idempotency tests live in `tests/integration/test_migration_####_*_idempotent.py` and must stay green.

## Frontend (Vitest)

### Locations

- Config: `frontend/apps/skriptoteket/vitest.config.ts`
- Setup: `frontend/apps/skriptoteket/src/test/setup.ts`
- Tests: `frontend/apps/skriptoteket/src/**/*.spec.ts`

### Commands

```bash
pdm run fe-test
pdm run fe-test-watch
pdm run fe-test-coverage
```

### Notes

- Prefer unit tests for pure helpers/composables; use `@vue/test-utils` only when component wiring matters.
- Coverage output is written under the SPA app (e.g. `frontend/apps/skriptoteket/coverage/`).

## UI / E2E (Playwright)

Use Playwright for browser-level flows and regressions (never Vitest).

Commands:

```bash
pdm run ui-smoke
pdm run ui-editor-smoke
pdm run ui-runtime-smoke
```

Reference:

- `.agent/rules/075-browser-automation.md`
