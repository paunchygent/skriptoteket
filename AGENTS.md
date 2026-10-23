# Skriptoteket

## Identity

Skriptoteket is a teacher-first Script Hub: a FastAPI/PostgreSQL backend, a
Vue/Vite SPA and curated apps, which are first-class application modules with
bespoke UX and app-specific APIs. Target Python is 3.13-3.14.

## Commands

Run from the repository root; the full list is in `pyproject.toml`.

- Docs and handoff: `pdm run docs-validate`, `handoff-validate`, `skills-validate`.
- Backend: `pdm run lint`, `typecheck`, `test`, `check`; dev: `dev`, `dev-stack`.
- Frontend: `pdm run fe-dev`, `fe-type-check`, `fe-lint`, `fe-test`, `fe-build`.

## Product Facts

- Skriptoteket is unreleased: until release, backward compatibility is no
  requirement unless the user states it for a named app. Keep no readers,
  defaults, aliases, fallbacks or dual paths for older data, schemas, payloads,
  settings or client state; change the format, delete the old path. Older formats
  are development intermediates, so plans and questions never raise lost saved
  data. Once teachers use it, data they depend on is migrated or kept readable.
- Paid AI is admin and superuser only until AI spend limits ship
  (TASK-SKRIPT-REP-0044): plan, walk and judge as if teachers have AI; behaviour
  only that gate causes is no issue.
- Paid overage (`ALLOW_PAID_OVERAGE`) after an LLM provider pool is used up is a
  user gate: stop, say the daily pool is used up, wait for the user's decision.
- HuleEdu owns shared browser-session login and identity; Skriptoteket keeps roles local.

## Local Routes

- State: `handoff.md`; history: `.codex/long-term-memory/index.md`; docs:
  `docs/index.md`; local skills: `.codex/skills/INDEX.md`.
- Topology and layer boundaries: `repo-code-map`; backend, UoW, migrations and
  runner contracts: `skriptoteket-backend-dev`; tests: `skriptoteket-testing`;
  pinball playfield geometry and board underlays: `pinball-board-authoring`.
- Staging and browser proof on Hemma: `staging-walk`; `skriptoteket-testing`
  states which changes are walked. UI: `huleedu-ui-design`, `integrated-frontend-stack`.
