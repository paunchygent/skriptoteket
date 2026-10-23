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

- Skriptoteket is an unreleased, iterative testbed: backward compatibility is
  never a requirement. Keep no readers, defaults, aliases, fallbacks or dual
  paths for older data, schemas, payloads, settings or stored client state;
  change the format and delete the old path. Compatibility applies only where
  the user states it explicitly for a named app.
- HuleEdu owns shared browser-session login and identity context; Skriptoteket
  keeps roles local.

## Local Routes

- Active state: `handoff.md`; session history: `.codex/long-term-memory/index.md`.
- Docs: `docs/index.md`; local skills: `.codex/skills/INDEX.md`.
- Topology and layer boundaries: `repo-code-map`; backend, UoW, migrations and
  runner contracts: `skriptoteket-backend-dev`; tests: `skriptoteket-testing`.
- Pinball playfield geometry and board underlays: `pinball-board-authoring`.
- Staging and browser proof on Hemma: `staging-walk`; UI work:
  `huleedu-ui-design`, `integrated-frontend-stack`.
