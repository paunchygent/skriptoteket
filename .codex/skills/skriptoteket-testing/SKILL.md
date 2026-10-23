---
name: skriptoteket-testing
description: Repo-local testing router for Skriptoteket. Use when planning, writing, reviewing, or running tests in this repo, including pytest backend tests, integration tests, migration tests, frontend Vitest lane selection, browser-walk proof routing, fixtures, smoke scripts, and close-out verification.
---

# Skriptoteket Testing

Use this skill as the repo-local testing decision surface. It owns the
Skriptoteket testing taxonomy and invariants; operational command detail lives
in repo docs-as-code, runbooks, and shared stack skills.

## Workflow

1. Classify the changed surface before choosing commands: domain/application,
   web API, infrastructure, migration, worker/runtime, frontend Vitest,
   browser proof, or app-specific smoke.
2. Load only the relevant reference below, then follow the docs-as-code sources
   it points to.
3. Prefer the smallest focused test that exercises the behavior, then run the
   required close-out gate for the touched layer.
4. Use named `pdm run ...` surfaces from the repo root. Do not invent raw
   commands when a repo wrapper exists.
5. Use the shared staging-walk skill for staging and browser proof on Hemma.

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
- Delete a test that asserts elapsed wall-clock time or a speed ratio; never
  harden it or propose a robust timing proof. A timeout that only bounds a
  wait for an observable result is fine.
- Migration tests must prove idempotency with the Docker/Testcontainers lane.

## Walk Scope

Walk only changes to the exam converter: the conversion hub exam tab, the
exam workspace, exam save and exports in Mina filer, the Exam.net import,
and the shared UI parts that app uses. Walk such a change once after it
merges, through the shared staging-walk skill on Hemma, and never re-walk
the whole app.

Every other UI change closes on an approved review plus unit tests, without
a walk. That covers restyle and style-token work, other curated apps,
admin and editor surfaces, and user-generated script tools.

Flunk-Out Frenzy is outside the user's focus: never ask the user about its
look, never walk it, and never hold a story for a finding that touches only
it. That work closes on review and unit proof.

## Reference Router

| Test area                                                          | Load                                |
| ------------------------------------------------------------------ | ----------------------------------- |
| Backend pytest, domain/application/API tests                       | `references/backend-pytest.md`      |
| Frontend Vitest/component tests                                    | `references/frontend-vitest.md`     |
| Browser walk, screenshots, authenticated UI proof                  | `## Walk Scope` above; the shared staging-walk skill runs the walk on Hemma |
| Alembic migrations and schema drift                                | `references/migrations.md`          |
| Worker/runtime, observability, PDF/export, curated-app specialties | `references/specialized-domains.md` |

## Close-Out Defaults

- Backend change: focused tests, then `pdm run lint` and `pdm run typecheck`.
- Frontend change: focused `pdm run fe-test ...`, then `pdm run fe-type-check`
  and `pdm run fe-lint`; add `pdm run fe-build` for shipped UI surfaces.
- Migration change: docker-marked migration test plus the documented dev DB
  upgrade lane.
- Exam-converter UI change: one staging walk after merge (see `## Walk Scope`).
- Docs or skill surface change: `pdm run skills-validate` when skills changed,
  `pdm run docs-validate` when docs or docs routing changed, and
  `git diff --check`.
