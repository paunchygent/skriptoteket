# Repository Guidelines

This repository hosts **Skriptoteket**, a teacher-first Script Hub with a Dockerized FastAPI backend and PostgreSQL.
UI is a Dockerized **Vue/Vite SPA** (see `docs/adr/adr-0027-full-vue-vite-spa.md`) hot-reloaded during development.
Target Python is **3.13–3.14**.

## Product Overview

- Roles: **users → contributors → admins → superuser**
- Findability: tools are tagged by **profession** and **category**; a tool can belong to multiple professions/categories
- Future: HuleEdu SSO is planned via identity federation (identity external; **roles remain local**)
- Curated apps are **first-class application modules** (shipped code), not tools.
- Curated apps MUST use bespoke UX + app-specific APIs; shared tool/runner infrastructure is internal-only.

## Engineering Rules (Non-Negotiable)

- ALWAYS do `sandbox_permissions=require_escalated` for all commands that need elevated permissions (i.e., targets outside the project directory)
- **No legacy support / workarounds**: do the full refactor; delete old paths instead of shims
- **No vibe-coding**: follow established patterns and rules in `.agents/rules/000-rule-index.md`
- **No unapproved reverts**: do not revert/restore changes you did not personally make without explicit user guidance (assume they may be user-added)
- **Session rule (REQUIRED)**: for any UI/route change, do a live functional check (run the backend and/or Vite as appropriate; verify it renders) and record how you verified it in `.agents/handoff.md`
- **Protocol-first DI**: depend on `typing.Protocol`, not concrete implementations
- **Layer boundaries**: domain is pure; web/api are thin; infrastructure implements protocols
- **Transactions**: Unit of Work owns commit/rollback; repositories never commit
- **Errors**: raise `DomainError` (no HTTP); map to HTTP in the web layer
- **Testing**: mock protocols; avoid `@patch` or implementation details - use DI and focus on behavior; keep test files <400–500 LOC
- **New agent/dev message**: when asked for a handoff message to a new developer/agent, generate it by filling `.agents/next-session-instruction-prompt-template.md` (address the recipient as “you”)

## Project Structure

- `src/skriptoteket/`: production code (DDD/Clean layers + DI + web)
- `migrations/`, `alembic.ini`: DB migrations (Alembic)
- **PDM/pyproject changes (incl. migration work)**: use `pdm-migration-specialist` for `pyproject.toml` dependency-group updates (generic skill; don’t import HuleEdu monorepo assumptions).
- `docs/`: PRD/ADRs/backlog (start at `docs/index.md`); contract-enforced via `docs/_meta/docs-contract.yaml`
- `docs/backlog/prs/`: technical PR tasks (refactors/structure work) connected to stories; use `docs/templates/template-pr.md`; validated by the docs contract like other doc types.
- **Docs workflow (REQUIRED)**: use the current docs-as-code flow described in `docs/index.md` and `docs/reference/ref-review-workflow.md`: `PRD -> ADR -> EPIC -> STORY -> PR backlog slices -> retained REVIEW` when a decision gate is needed.
- **Docs index (REQUIRED)**: when adding new docs, update `docs/index.md` so the full index stays complete.
- **Epic update workflow (REQUIRED)**: when you mark a story `done`, update its epic in `docs/backlog/epics/`:
  - bump the epic frontmatter `updated` date
  - add/refresh a short “Implementation Summary (as of YYYY-MM-DD)” noting what shipped (at minimum the story ID)
- **Handoff workflow (REQUIRED)**: when you change any story/epic/PR/review status (or scope/dependencies), update `.agents/handoff.md`:
  - Keep `## Snapshot` fields current.
  - Do **not** include commit SHAs in Snapshot (avoid churn); use `Branch: <name> + local changes`.
  - Add the relevant verification commands/manual checks under `## Verification`.
  - When compacting `.agents/handoff.md`, append the removed content directly to `docs/reference/ref-development-changelog.md` first.
- **Review workflow (REQUIRED)**: all proposed EPICs/ADRs must be reviewed before implementation — see `docs/reference/ref-review-workflow.md` and `.agents/rules/096-review-workflow.md`
- `frontend/`: pnpm workspace (Vue/Vite) — `apps/skriptoteket` (SPA), `packages/huleedu-ui` (component library)
- `.agents/`: agent workflow helpers (`.agents/handoff.md`, next-session prompt template) + coding rules (`.agents/rules/`)
- `.claude/skills/`: repo-local agent skills (workflow playbooks + helpers)
- `scripts/`: repo tooling (e.g., `scripts/validate_docs.py`)

## Key Commands

- Setup: `pdm install -G monorepo-tools`
- Pre-commit (REQUIRED): `pdm run precommit-install` then `pdm run precommit-run` (`pre-commit` includes ShellCheck for staged `.sh` / `.bash` files)
- DB (dev): `docker compose up -d db` then `pdm run db-upgrade`
- Bootstrap first superuser: `pdm run bootstrap-superuser`
- Run: `pdm run dev`
- Run (local + log piping): `pdm run dev-logs` (writes `.artifacts/dev-backend.log`)
- Run (local combo): `pdm run dev-local` (backend + SPA with log piping)
- Execution worker (one-off dev): `pdm run run-execution-worker --once`
- Dev logs: when using Vite (`pdm run fe-dev`), API calls proxy to `127.0.0.1:8000` → check the **host** `pdm run dev` terminal for backend errors (container logs only apply if you point the UI at the container port).
- Frontend deps: `pdm run fe-install` (or `pnpm -C frontend install`)
- SPA dev: `pdm run fe-dev` (or `pnpm -C frontend --filter @skriptoteket/spa dev`)
- SPA dev (local + log piping): `pdm run fe-dev-logs` (writes `.artifacts/dev-frontend.log`)
- SPA build: `pdm run fe-build` (or `pnpm -C frontend --filter @skriptoteket/spa build`)
- SPA tests (Vitest): `pdm run fe-test` / `pdm run fe-test-watch` / `pdm run fe-test-coverage`
- SPA typecheck: `pdm run fe-type-check`
- **Dev services are long-running**: do not stop `pdm run dev` or `docker compose up -d db` unless explicitly requested.
- Docker dev workflow: `pdm run dev-start` / `pdm run dev-stop` / `pdm run dev-build-start` / `pdm run dev-build-start-clean` / `pdm run dev-rebuild` / `pdm run dev-db-reset`
- Docker dev logs (web + worker + frontend): `pdm run dev-containers-logs`
- **Docker image builds (REQUIRED)**: run in background, log to `.artifacts/`, and give the user the `tail -f` command.
- Quality: `pdm run format` / `pdm run lint` / `pdm run typecheck` / `pdm run test`
- Shell quality: `pdm run shellcheck <paths...>` while iterating on shell scripts; `pdm run lint` is the required final close-out gate and includes repo-wide `pdm run shellcheck-all`
- Docs: `pdm run docs-validate`
- Session file ops (prod): `pdm run cleanup-session-files` (TTL cleanup) / `pdm run clear-all-session-files` (danger: deletes all)
- Skills prompt: `pdm run skills-prompt` / `pdm run skills-validate`
- Hemma deploy launcher: `pdm run hemma-deploy` / `pdm run hemma-deploy-monitor`

## SSH Defaults (hemma)

- `ssh hemma` uses non-root user `paunchygent` (key: `~/.ssh/hemma-paunchygent_ed25519`).
- Root access requires explicit approval; use `ssh hemma-root` when needed.
- LAN aliases: `ssh hemma-local` (non-root), `ssh hemma-local-root` (root).
Switch to run bash on hemma via heredocs to avoid nested quoting issues.
- Hemma storage tiers are explicit:
  - `/srv/scratch` = fast SSD working tier for Docker root/BuildKit cache,
    HF/model caches, and active generated artifacts.
  - `/srv/storage` = large HDD bulk-data tier for raw corpora and cold retained
    datasets.
  - `/` must not be the long-term home for Docker persistent state or large ML
    artifact trees.

## Skill Usage (REQUIRED)

- Skills are provided at session start from `$CODEX_HOME/skills` (typically `~/.codex/skills/*/SKILL.md`) and repo-local `.claude/skills/*/SKILL.md`.
- Load the relevant repo/domain skill before planning or implementation work. Treat skills as the procedural layer and keep `AGENTS.md` focused on repo policy.
- Minimum expected defaults:
  - `skriptoteket-local-devops` for local development, DB/migrations, and dev-runtime troubleshooting
  - `skriptoteket-frontend-specialist` for SPA and curated-app frontend work
  - `playwright-testing` before planning, writing, running, or reviewing Playwright automation
  - the relevant observability skill when debugging Grafana/Prometheus/Loki/Jaeger/structured logging. Live baseline is always on <http://127.0.0.1:5173> for dev.

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

- Follow `.agents/rules/000-rule-index.md` (protocol-first DI, UoW-owned transactions, no business logic in web layer)
- Keep files small (<400–500 LOC); Ruff format + lint (100 chars)
- Use Pydantic for cross-boundary models; `dataclasses` only inside a single domain
- Frontend unit/integration tests use Vitest: `frontend/apps/skriptoteket/vitest.config.ts`, tests in `frontend/apps/skriptoteket/src/**/*.spec.ts`

### Browser Automation

Playwright is the default for browser automation. Follow `.agents/rules/075-browser-automation.md` and the
`playwright-testing` skill for operational details, script structure, and credential handling.

Repo-specific reminders:

- For quick UI fixes/checkups in Codex, use headed Playwright MCP Chrome first and follow the rule/skill recovery flow exactly. Do not fall back to headless because of a profile-lock error; the canonical MCP config is `--browser chrome --isolated`.
- Reuse the bootstrap superuser from `.env` for local UI checks; do not create ad hoc dev accounts.
- Seed required Playwright tool fixtures through `src/skriptoteket/script_bank/` instead of creating demo tools in the DB.

## Git Workflow

- **Never use `git commit --amend`**: always create fresh commits for fixes discovered after the initial commit
- **Never force push**: if you need to fix something, make a new commit
- Runbooks in `docs/runbooks/` are first-class, versioned docs; commit updates (no local-only runbook edits)
- Include what/why + how to test in commit messages
- Run `pdm run docs-validate` for doc changes

## Agent docs size budgets (enforced)

- Keep `.agents/handoff.md` ≤ 200 lines (enforced by pre-commit).
- `.agents/handoff.md` should only keep current delivery-critical backend/frontend info.
- When pruning `.agents/handoff.md`, move the removed content directly to `docs/reference/ref-development-changelog.md` with minimal reshaping.

## Observability Stack

Public URLs (credentials in `~/apps/skriptoteket/.env` on server):

- <https://grafana.hemma.hule.education> (admin / `GRAFANA_ADMIN_PASSWORD`)
- <https://prometheus.hemma.hule.education> (admin / `PROMETHEUS_BASIC_AUTH_PASSWORD`)

Reset Grafana password: `ssh hemma "sudo docker exec grafana grafana cli admin reset-admin-password '<pw>'"` (env var only works on first startup).
Use the appropriate observability skill when troubleshooting (metrics/logs/traces/structured logging).

## AI Inference Infrastructure

| Service      | Port | Purpose                                  |
|--------------|------|------------------------------------------|
| llama-server | 8082 | ROCm GPU inference (Qwen3-Coder-30B-A3B) |
| tabby        | 8083 | Code completion API (`/v1/completions`)  |

Health check: `ssh hemma "curl -s http://localhost:8083/v1/health | jq .model"`

Runbooks: `docs/runbooks/runbook-gpu-ai-workloads.md`, `docs/runbooks/runbook-tabby-codemirror.md`

## Security

- Never commit secrets (API keys/tokens); use env vars / `.env` locally

## OpenAI Guidance (REQUIRED)

- Do not trust training data for OpenAI model parameters or caching behavior.
- Always defer to `docs/runbooks/runbook-openai-responses-api.md` for OpenAI-related work
  (Responses API, model parameters, caching, best practices).
