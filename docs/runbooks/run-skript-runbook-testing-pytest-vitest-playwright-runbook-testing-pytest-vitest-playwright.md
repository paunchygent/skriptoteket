---
type: runbook
id: RUN-SKRIPT-runbook-testing-pytest-vitest-playwright
title: 'Runbook: Testing (Pytest + Vitest + Playwright)'
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: active
retired_ids:
- RUN-testing
summary: 'Runbook: Testing (Pytest + Vitest + Playwright)'
system: skriptoteket-dev
---

## Trigger
### Source record
This runbook describes how to run tests locally (and what each suite is responsible for).
### Quick start
```bash
### Backend checks
pdm run lint
pdm run typecheck
pdm run test

### Frontend checks
pdm run fe-type-check
pdm run fe-lint
pdm run fe-test

### UI smoke (Playwright)
pdm run pr-0253-auth-retirement --start-backend --start-vite
pdm run pr-0255-auth-bootstrap --start-backend --start-vite
```
### Changed-component quality

For normal repository changes, use the package-owned changed-component gate:

```bash
pdm run check
```

### Backend (Pytest)
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

- Use the canonical `pdm run test` surface for WeasyPrint-backed PDF renderer
  tests. On macOS, that wrapper starts pytest with Homebrew/MacPorts native
  library directories available to the child process before WeasyPrint imports
  Pango, Harfbuzz, Fontconfig, and GObject.
- If native libraries live outside `/opt/homebrew/lib`, `/usr/local/lib`, or
  `/opt/local/lib`, set `SKRIPTOTEKET_NATIVE_LIBRARY_DIRS` to an
  `os.pathsep`-separated list before running `pdm run test`.
- Avoid raw `pytest` for local PDF renderer debugging; it can miss the native
  library environment that the repo command surface deliberately supplies.
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
### Frontend (Vitest)
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
### UI / E2E (Playwright)
Use Playwright for browser-level flows and regressions (never Vitest).

For protected shared-auth flows, run Skriptoteket through the Docker `web`
service (`skriptoteket_web`, alias `skriptoteket-web`) so HuleEdu Gateway can
reach app continuation through `hule-network`. Host Uvicorn is not a valid
backend for Gateway-authenticated browser proof.

For host Vite shared-auth proof, use the split local lane:

```bash
pdm run dev-stack web-start
pdm run fe-dev-shared-auth
```

This keeps protected `/api/...` calls on the local HuleEdu Gateway while public
`/api/v1/public/...` calls continue to use the Docker-backed Skriptoteket web
service. If public app routes return a Vite-level `500 Internal Server Error`,
first verify that the Docker `web` service is running and reachable on
`http://localhost:8000`.

Commands:

```bash
pdm run pr-0253-auth-retirement --start-backend --start-vite
pdm run pr-0255-auth-bootstrap --start-backend --start-vite
pdm run pr-0252-auth-return --start-backend --start-vite
```

Reference:

- `.codex/rules/075-browser-automation.md`
- `docs/runbooks/runbook-agent-browser-automation.md`

## Preconditions
The source record did not define a separate section for this package heading.

## Steps
The source record did not define a separate section for this package heading.

## Expected Results
The source record did not define a separate section for this package heading.

## Stop Conditions
The source record did not define a separate section for this package heading.

## Rollback
The source record did not define a separate section for this package heading.
