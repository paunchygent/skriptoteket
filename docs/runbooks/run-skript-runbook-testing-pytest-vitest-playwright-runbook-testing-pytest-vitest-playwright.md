---
type: runbook
id: RUN-SKRIPT-runbook-testing-pytest-vitest-playwright
title: 'Runbook: Testing (Pytest + Vitest + browser walk)'
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: active
retired_ids:
- RUN-testing
summary: 'Runbook: Testing (Pytest + Vitest + browser walk)'
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
```

Use the shared staging-walk skill for staging and browser proof on Hemma.
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
pdm run pytest tests/unit/domain/curated_apps
pdm run test-docker
pdm run test-simulations
```

- `pdm run test` runs the changed-component route; `pdm run pytest <target>`
  runs a focused target. Both run in parallel (`-n logical --dist worksteal` in
  `addopts`) and quietly: no live log streaming, and captured INFO logs and
  stdout are printed only for failing tests.
- The worker count follows the selection: fewer than 12 files run
  in-process, a larger run gets one worker per 6 files, capped by the hardware
  threads. A sweep file that declares `# xdist-weight: <n>` counts as `n` files.
- `pdm run test-docker` runs the Docker integration lane. Each worker starts
  one Postgres container and migrates one template database; every module
  gets its own copy of it.
- A serial run must state why. `-n 0`, `--pdb` or an overridden `addopts`
  stops with a usage error unless `--serial-reason "<reason>"` is given. Use
  the named serial route only to step through a test with `--pdb` or to read
  live log output of one failing test:

```bash
pdm run test-serial --serial-reason "live log of the curated-app model test" tests/unit/domain/curated_apps/test_models.py
```

### Notes

- Integration tests use Docker (testcontainers). Ensure Docker Desktop is running and accessible.
- Migration idempotency tests live in `tests/integration/test_migration_####_*_idempotent.py` and must stay green.

### Local PDF renderer checks

- Use the canonical `pdm run test` or `pdm run pytest` surface for
  WeasyPrint-backed PDF renderer tests. On macOS, that wrapper starts pytest with Homebrew/MacPorts native
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
### UI / E2E (browser walk)

Use the shared staging-walk skill for staging and browser proof on Hemma.

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
