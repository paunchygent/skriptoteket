# Repository Guidelines

This repository hosts **Skriptoteket**, a teacher-first Script Hub built with FastAPI (server-rendered UI) and PostgreSQL.
Target Python is **3.13–3.14**.

## Product Overview

- Roles: **users → contributors → admins → superuser**
- Findability: tools are tagged by **profession** and **category**; a tool can belong to multiple professions/categories
- Future: HuleEdu SSO is planned via identity federation (identity external; **roles remain local**)

## Engineering Rules (Non-Negotiable)

- **No legacy support / workarounds**: do the full refactor; delete old paths instead of shims
- **No vibe-coding**: follow established patterns and rules in `.agent/rules/000-rule-index.md`
- **No unapproved reverts**: do not revert/restore changes you did not personally make without explicit user guidance (assume they may be user-added)
- **Session rule (REQUIRED)**: for any UI/route change, do a live functional check (run the app and verify the page renders) and record how you verified it in `.agent/handoff.md`
- **Protocol-first DI**: depend on `typing.Protocol`, not concrete implementations
- **Layer boundaries**: domain is pure; web/api are thin; infrastructure implements protocols
- **Transactions**: Unit of Work owns commit/rollback; repositories never commit
- **Errors**: raise `DomainError` (no HTTP); map to HTTP in the web layer
- **Testing**: mock protocols; avoid `@patch` or implementation details - use DI and focus on behavior; keep test files <400–500 LOC
- **New agent/dev message**: when asked for a handoff message to a new developer/agent, generate it by filling `.agent/next-session-instruction-prompt-template.md` (address the recipient as “you”)

## Project Structure

- `src/skriptoteket/`: production code (DDD/Clean layers + DI + web)
- `migrations/`, `alembic.ini`: DB migrations (Alembic)
- `docs/`: PRD/ADRs/backlog (start at `docs/index.md`); contract-enforced via `docs/_meta/docs-contract.yaml`
- **Docs workflow (REQUIRED)**: follow `docs/reference/ref-sprint-planning-workflow.md` for PRD → ADR → epic → story → sprint planning.
- `.agent/`: agent workflow helpers (`.agent/readme-first.md`, `.agent/handoff.md`, prompt template) + coding rules (`.agent/rules/`)
- `scripts/`: repo tooling (e.g., `scripts/validate_docs.py`)

## Key Commands

- Setup: `pdm install -G monorepo-tools`
- DB (dev): `docker compose up -d db` then `pdm run db-upgrade`
- Bootstrap first superuser: `pdm run bootstrap-superuser`
- Run: `pdm run dev`
- Docker dev workflow: `pdm run dev-start` / `pdm run dev-stop` / `pdm run dev-build-start` / `pdm run dev-build-start-clean` / `pdm run dev-db-reset`
- Quality: `pdm run format` / `pdm run lint` / `pdm run typecheck` / `pdm run test`
- Docs: `pdm run docs-validate`

## Tool Execution (Local Dev Only)

Before running tool execution locally:

```bash
# Add to .env
ARTIFACTS_ROOT=/tmp/skriptoteket/artifacts

# Create directory
mkdir -p /tmp/skriptoteket/artifacts
```

The default `ARTIFACTS_ROOT=/var/lib/skriptoteket/artifacts` doesn't exist locally and will cause 500 errors on tool execution.

## Coding & Testing Rules

- Follow `.agent/rules/000-rule-index.md` (protocol-first DI, UoW-owned transactions, no business logic in web layer)
- Keep files small (<400–500 LOC); Ruff format + lint (100 chars)
- Use Pydantic for cross-boundary models; `dataclasses` only inside a single domain

## Git Workflow

- **Never use `git commit --amend`**: always create fresh commits for fixes discovered after the initial commit
- **Never force push**: if you need to fix something, make a new commit
- Include what/why + how to test in commit messages
- Run `pdm run docs-validate` for doc changes

## Security

- Never commit secrets (API keys/tokens); use env vars / `.env` locally
