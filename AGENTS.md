# Repository Guidelines

This repository hosts a teacher-first **Script Hub** service built with FastAPI and managed with PDM (`pyproject.toml`).
Target Python is **3.13** (keep 3.14-compatibility in mind).

## Product Overview & Users

- Roles: **users → contributors → admins → superuser**.
- Tools/scripts are organized by **profession** (e.g., `lärare`, `specialpedagog`, `skoladministratör`, `rektor`) and **category** (e.g., `lektionsplanering`, `mentorskap`, `administration`, `övrigt`).
- A script may belong to **multiple** professions/categories (multi-tagging).

## Project Structure & Module Organization

- `app/`: FastAPI entrypoint (currently `app/main.py`).
- `docs/`: PRD/ADRs/backlog (start at `docs/index.md`); contract-enforced via `docs/_meta/docs-contract.yaml` (use templates, set `owners: ["agents"]`; ADRs also set `deciders: ["user-lead"]`).
- `scripts/`: repo tooling (e.g., `scripts/validate_docs.py`).
- `.agent/`: project rules/patterns (start at `.agent/rules/000-rule-index.md`).
- `jupyter_scripts/`: exploratory notebooks (not production code).

## Build, Test, and Development Commands

Use PDM for local development:

- `pdm install -G monorepo-tools`: install deps + tooling.
- `pdm run dev`: run locally with reload.
- `pdm run format` / `pdm run lint` / `pdm run typecheck`: format, lint, type-check.
- `pdm run test`: run tests (default excludes `financial`, `slow`, `docker`).
- `pdm run docs-validate`: validate `docs/` structure/frontmatter (run before PRs).

Docker (optional):

- `pdm export -o requirements.txt --no-hashes` then `docker compose up --build`.

## Coding Style & Naming Conventions

- Indentation: 4 spaces; max line length: 100; use Ruff formatting + import sorting.
- Naming: modules `snake_case.py`, classes `PascalCase`, functions/vars `snake_case`, constants `UPPER_SNAKE_CASE`.
- Architecture: strict DDD + Clean Architecture, SRP modules (aim <400–500 LOC), protocol-first DI, async-first.
- Models: Pydantic for cross-domain/boundary DTOs; `dataclasses` only within a single domain.

## Testing Guidelines

- Framework: `pytest` (configured in `pyproject.toml`).
- Place tests in `tests/` and name them `test_*.py` (or `*_test.py`) when introduced.
- Use markers to communicate intent: `unit`, `integration`, `e2e`, `slow`, `docker`, `financial`.
  Default options exclude `financial`, `slow`, and `docker`.

## Commit & Pull Request Guidelines

- No Git history is present in this checkout; use clear, imperative commits (recommended: Conventional Commits like `feat: ...`, `fix: ...`, `chore: ...`).
- PRs should include: what/why, how to test (`pdm run …`), and screenshots for UI changes.

## Security & Configuration Tips

- Keep secrets out of the repo; use environment variables and optional `.env`.
- Treat uploaded files as untrusted input; avoid executing user-provided code.
