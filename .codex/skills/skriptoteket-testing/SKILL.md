---
name: skriptoteket-testing
description: Repo-local testing router for Skriptoteket. Use when planning, writing, reviewing, or running tests in this repo, including pytest backend tests, integration tests, migration tests, frontend Vitest lane selection, Playwright/browser proof routing, fixtures, smoke scripts, and close-out verification.
---

# Skriptoteket Testing

Use this skill as the repo-local testing decision surface. It owns the
Skriptoteket testing taxonomy and invariants; operational command detail lives
in repo docs-as-code, rules, runbooks, and shared stack skills.

## Workflow

1. Classify the changed surface before choosing commands: domain/application,
   web API, infrastructure, migration, worker/runtime, frontend Vitest,
   browser proof, or app-specific smoke.
1. Load only the relevant reference below, then follow the docs-as-code sources
   it points to.
1. Prefer the smallest focused test that exercises the behavior, then run the
   required close-out gate for the touched layer.
1. Use named `pdm run ...` surfaces from the repo root. Do not invent raw
   commands when a repo wrapper exists.
1. If a UI route, auth path, or browser-visible behavior changes, run a live
   functional check and record the exact proof in `.codex/handoff.md`.

## Invariants

- Test public contracts and user-visible behavior, not implementation trivia.
- Mock protocols and ports of the architecture, not concrete internals.
- Keep unit tests fast and deterministic: no Docker, network, persistent DB, or
  wall-clock dependence.
- Use integration tests for real repository, migration, filesystem, worker, and
  gateway seams.
- Keep `tests/conftest.py` minimal; put fixtures and helpers in explicit
  `tests/fixtures/` modules.
- A test that requires broad monkeypatching usually signals the production
  boundary needs a protocol, DI seam, or smaller module.
- Browser/protected-API proof must use the HuleEdu browser-session ceremony and
  repo helpers. Raw Vite inspection is not authenticated proof.
- Migration tests must prove idempotency with the Docker/Testcontainers lane.

## Reference Router

| Test area | Load |
|---|---|
| Backend pytest, domain/application/API tests | `references/backend-pytest.md` |
| Frontend Vitest/component tests | `references/frontend-vitest.md` |
| Browser automation, screenshots, authenticated UI proof | `references/browser-automation.md` |
| Alembic migrations and schema drift | `references/migrations.md` |
| Worker/runtime, observability, PDF/export, curated-app specialties | `references/specialized-domains.md` |

## Close-Out Defaults

- Backend change: focused tests, then `pdm run lint` and `pdm run typecheck`.
- Frontend change: focused `pdm run fe-test ...`, then `pdm run fe-type-check`
  and `pdm run fe-lint`; add `pdm run fe-build` for shipped UI surfaces.
- Migration change: docker-marked migration test plus the documented dev DB
  upgrade lane.
- Browser-visible change: live browser proof through the appropriate local
  stack; authenticated paths use HuleEdu Gateway, not local shortcuts.
- Docs or skill surface change: `pdm run skills-validate` when skills changed,
  `pdm run docs-validate` when docs or docs routing changed, and
  `git diff --check`.
