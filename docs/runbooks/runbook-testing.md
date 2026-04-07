---
type: runbook
id: RUN-testing
title: "Runbook: Testing (Pytest + Vitest + Playwright)"
status: active
owners: "agents"
created: 2025-12-29
updated: 2026-03-26
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

### Local PDF renderer checks

- For WeasyPrint renderers built from `HTML(string=...)`, treat relative image/logo URLs as invalid
  unless `base_url` is supplied.
- The repo-safe pattern is to pass the asset directory itself as a filesystem `Path` (or plain
  directory path string) and keep asset references relative, for example
  `HTML(string=html, base_url=assets_dir)`.
- Do not use `assets_dir.as_uri()` as a directory base unless you also prove the URI form resolves
  correctly in the current renderer. During local verification on `2026-03-26`, the URI-directory
  form without a trailing slash resolved relative assets one directory too high and silently
  dropped the logo from exported PDFs.
- When a PDF asset is missing, enable WeasyPrint logging and run a small focused probe before
  changing production code. The expected failure signature is a fetch path that has lost the final
  asset-directory segment.

### Klassrumskartan PDF export rule

- Klassrumskartan app-owned PDF artifacts should render locally inside Skriptoteket.
- Practical rule:
  - local in-process WeasyPrint renderer: `base_url` + relative asset path
  - do not route Klassrumskartan-owned PDF export rendering through Sir Convert-a-Lot
- Sir Convert remains relevant for general conversion workloads such as Conversion Hub and
  class-list import PDF extraction.

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
- The canonical filtered command surface is `pdm run fe-test ...` (or `pnpm -C frontend/apps/skriptoteket test ...`), not raw `pnpm ... exec vitest ...`.
- The SPA wrapper now normalizes both app-local targets like `src/views/apps/ClassroomPlannerEntryView.spec.ts` and repo-root targets like `frontend/apps/skriptoteket/src/views/apps/ClassroomPlannerEntryView.spec.ts`.

## UI / E2E (Playwright)

Use Playwright for browser-level flows and regressions (never Vitest).

Commands:

```bash
pdm run ui-smoke
pdm run ui-editor-smoke
pdm run ui-runtime-smoke
```

Reference:

- `.agents/rules/075-browser-automation.md`
- `docs/runbooks/runbook-agent-browser-automation.md`
