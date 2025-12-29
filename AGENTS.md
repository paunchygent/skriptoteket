# Repository Guidelines

This repository hosts **Skriptoteket**, a teacher-first Script Hub with a FastAPI backend and PostgreSQL.
UI is a **Vue/Vite SPA** (see `docs/adr/adr-0027-full-vue-vite-spa.md`); legacy SSR/Jinja/HTMX has been removed after cutover.
Target Python is **3.13–3.14**.

## Product Overview

- Roles: **users → contributors → admins → superuser**
- Findability: tools are tagged by **profession** and **category**; a tool can belong to multiple professions/categories
- Future: HuleEdu SSO is planned via identity federation (identity external; **roles remain local**)

## Engineering Rules (Non-Negotiable)

- **No legacy support / workarounds**: do the full refactor; delete old paths instead of shims
- **No vibe-coding**: follow established patterns and rules in `.agent/rules/000-rule-index.md`
- **No unapproved reverts**: do not revert/restore changes you did not personally make without explicit user guidance (assume they may be user-added)
- **Session rule (REQUIRED)**: for any UI/route change, do a live functional check (run the backend and/or Vite as appropriate; verify it renders) and record how you verified it in `.agent/handoff.md`
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
- **Review workflow (REQUIRED)**: all proposed EPICs/ADRs must be reviewed before implementation — see `docs/reference/ref-review-workflow.md` and `.agent/rules/096-review-workflow.md`
- `frontend/`: pnpm workspace (Vue/Vite) — `apps/skriptoteket` (SPA), `packages/huleedu-ui` (component library)
- `.agent/`: agent workflow helpers (`.agent/readme-first.md`, `.agent/handoff.md`, prompt template) + coding rules (`.agent/rules/`)
- `.claude/skills/`: repo-local agent skills (workflow playbooks + helpers)
- `scripts/`: repo tooling (e.g., `scripts/validate_docs.py`)

## Key Commands

- Setup: `pdm install -G monorepo-tools`
- Pre-commit (REQUIRED): `pdm run precommit-install` then `pdm run precommit-run`
- DB (dev): `docker compose up -d db` then `pdm run db-upgrade`
- Bootstrap first superuser: `pdm run bootstrap-superuser`
- Run: `pdm run dev`
- Frontend deps: `pdm run fe-install` (or `pnpm -C frontend install`)
- SPA dev: `pdm run fe-dev` (or `pnpm -C frontend --filter @skriptoteket/spa dev`)
- SPA build: `pdm run fe-build` (or `pnpm -C frontend --filter @skriptoteket/spa build`)
- SPA tests (Vitest): `pdm run fe-test` / `pdm run fe-test-watch` / `pdm run fe-test-coverage`
- **Dev services are long-running**: do not stop `pdm run dev` or `docker compose up -d db` unless explicitly requested.
- Docker dev workflow: `pdm run dev-start` / `pdm run dev-stop` / `pdm run dev-build-start` / `pdm run dev-build-start-clean` / `pdm run dev-db-reset`
- Quality: `pdm run format` / `pdm run lint` / `pdm run typecheck` / `pdm run test` (lint runs Ruff + agent-doc budgets + docs contract)
- Docs: `pdm run docs-validate`
- Session file ops (prod): `pdm run cleanup-session-files` (TTL cleanup) / `pdm run clear-all-session-files` (danger: deletes all)
- Skills prompt: `pdm run skills-prompt` / `pdm run skills-validate` (scans `.claude/skills/`)

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
- Frontend unit/integration tests use Vitest: `frontend/apps/skriptoteket/vitest.config.ts`, tests in `frontend/apps/skriptoteket/src/**/*.spec.ts`

### Browser Automation

Playwright is the default for new browser automation (see `.agent/rules/075-browser-automation.md`).
Run smokes with `pdm run ui-smoke` / `pdm run ui-editor-smoke` / `pdm run ui-runtime-smoke`, or ad-hoc scripts via
`pdm run python -m scripts.<module>`.

- **Do not create new superusers for UI checks**: reuse the existing local dev bootstrap account in `.env`
  (`BOOTSTRAP_SUPERUSER_EMAIL` / `BOOTSTRAP_SUPERUSER_PASSWORD`). Creating new accounts bloats the dev DB.
- **Do not create ad hoc demo tools/scripts for Playwright**: if a browser automation script needs a specific tool by
  slug, add it to the repo script bank (`src/skriptoteket/script_bank/`) and run `pdm run seed-script-bank --slug <slug>`
  (optionally `--sync-code`) before running Playwright. This avoids polluting the dev DB (see `.agent/rules/075-browser-automation.md`).
- **Prod smoke tests (recommended)**: keep `BOOTSTRAP_SUPERUSER_*` for provisioning/local dev; store prod UI smoke
  credentials in a gitignored `.env.prod-smoke` (`BASE_URL`, `PLAYWRIGHT_EMAIL`, `PLAYWRIGHT_PASSWORD`) and run
  `pdm run ui-smoke --dotenv .env.prod-smoke` (same for `ui-editor-smoke` / `ui-runtime-smoke`).

## Git Workflow

- **Never use `git commit --amend`**: always create fresh commits for fixes discovered after the initial commit
- **Never force push**: if you need to fix something, make a new commit
- Include what/why + how to test in commit messages
- Run `pdm run docs-validate` for doc changes

## Agent docs size budgets (enforced)

- Keep `.agent/readme-first.md` ≤ 300 lines and `.agent/handoff.md` ≤ 200 lines (enforced by pre-commit).
- `.agent/handoff.md` should only keep current sprint-critical backend/frontend info; move completed story detail to
  `.agent/readme-first.md` (links only) + `docs/`.

## Observability Stack

Public URLs (credentials in `~/apps/skriptoteket/.env` on server):
- https://grafana.hemma.hule.education (admin / `GRAFANA_ADMIN_PASSWORD`)
- https://prometheus.hemma.hule.education (admin / `PROMETHEUS_BASIC_AUTH_PASSWORD`)

Reset Grafana password: `ssh hemma "docker exec grafana grafana cli admin reset-admin-password '<pw>'"` (env var only works on first startup).

## Security

- Never commit secrets (API keys/tokens); use env vars / `.env` locally

<available_skills>
  <skill>
    <name>brutalist-academic-ui</name>
    <description>Opinionated frontend design for brutalist and academic interfaces. Grid-based layouts, systematic typography, monospace/serif pairings, high-contrast schemes. HTML, CSS, Tailwind, vanilla JS.</description>
    <location>/Users/olofs_mba/Documents/Repos/CascadeProjects/windsurf-project/.claude/skills/brutalist-academic-ui/SKILL.md</location>
  </skill>
  <skill>
    <name>claude-hooks-developer</name>
    <description>Create, configure, and manage Claude Code hooks for workflow automation, validation, and security. Guides hook implementation, configuration patterns, and best practices.</description>
    <location>/Users/olofs_mba/Documents/Repos/CascadeProjects/windsurf-project/.claude/skills/hooks/SKILL.md</location>
  </skill>
  <skill>
    <name>distributed-tracing-specialist</name>
    <description>Configure and use OpenTelemetry distributed tracing with Jaeger in HuleEdu services. Guides tracer initialization, span creation, W3C trace propagation, and correlation with logs/metrics. Integrates with Context7 for latest OpenTelemetry documentation.</description>
    <location>/Users/olofs_mba/Documents/Repos/CascadeProjects/windsurf-project/.claude/skills/distributed-tracing/SKILL.md</location>
  </skill>
  <skill>
    <name>jaeger-tracing-specialist</name>
    <description>Jaeger/OpenTelemetry patterns plus Skriptoteket tracing conventions (async context propagation, correlation, debugging).</description>
    <location>/Users/olofs_mba/Documents/Repos/CascadeProjects/windsurf-project/.claude/skills/jaeger-tracing/SKILL.md</location>
  </skill>
  <skill>
    <name>loki-logql-query-specialist</name>
    <description>Query and analyze logs using Loki and LogQL. Provides patterns for correlation ID tracing, error investigation, and service debugging using HuleEdu's structured logging. Integrates with Context7 for latest Loki documentation.</description>
    <location>/Users/olofs_mba/Documents/Repos/CascadeProjects/windsurf-project/.claude/skills/loki-logql/SKILL.md</location>
  </skill>
  <skill>
    <name>pdm-migration-specialist</name>
    <description>Migrate pyproject.toml from pre-PDM 2.0 syntax to modern PEP-compliant format. Focuses on dev-dependencies to dependency-groups conversion and PEP 621 project metadata. Integrates with Context7 for latest PDM documentation.</description>
    <location>/Users/olofs_mba/Documents/Repos/CascadeProjects/windsurf-project/.claude/skills/pdm/SKILL.md</location>
  </skill>
  <skill>
    <name>playwright-testing</name>
    <description>Browser automation with Playwright for Python. Recommended for visual testing. (project)</description>
    <location>/Users/olofs_mba/Documents/Repos/CascadeProjects/windsurf-project/.claude/skills/playwright-testing/SKILL.md</location>
  </skill>
  <skill>
    <name>prometheus-metrics-specialist</name>
    <description>Instrument services with Prometheus metrics and write PromQL queries. Guides HuleEdu naming conventions, metrics middleware setup, and business vs operational metrics. Integrates with Context7 for latest Prometheus documentation.</description>
    <location>/Users/olofs_mba/Documents/Repos/CascadeProjects/windsurf-project/.claude/skills/prometheus-metrics/SKILL.md</location>
  </skill>
  <skill>
    <name>puppeteer-visual-testing</name>
    <description>Screenshot capture and visual testing with Puppeteer v24.x for Vue frontend. (project)</description>
    <location>/Users/olofs_mba/Documents/Repos/CascadeProjects/windsurf-project/.claude/skills/puppeteer-visual-testing/SKILL.md</location>
  </skill>
  <skill>
    <name>repomix-package-builder</name>
    <description>Create targeted repomix XML packages for AI code analysis. Suggests templates (metadata-flow, code-review, architecture, context) and file patterns based on task objectives. See reference.md for detailed workflows and patterns.</description>
    <location>/Users/olofs_mba/Documents/Repos/CascadeProjects/windsurf-project/.claude/skills/repomix/SKILL.md</location>
  </skill>
  <skill>
    <name>selenium-testing</name>
    <description>Browser automation with Selenium WebDriver for Python. (project)</description>
    <location>/Users/olofs_mba/Documents/Repos/CascadeProjects/windsurf-project/.claude/skills/selenium-testing/SKILL.md</location>
  </skill>
  <skill>
    <name>skriptoteket-devops</name>
    <description>DevOps and server management for Skriptoteket on home server (hemma.hule.education). Branched skill covering deploy, database, users, CLI, security, network, DNS, and troubleshooting.</description>
    <location>/Users/olofs_mba/Documents/Repos/CascadeProjects/windsurf-project/.claude/skills/skriptoteket-devops/SKILL.md</location>
  </skill>
  <skill>
    <name>structlog-logging-specialist</name>
    <description>Configure and use Structlog for structured logging in HuleEdu services. Guides correlation context propagation, async-safe logging, and integration with error handling. Integrates with Context7 for latest Structlog documentation.</description>
    <location>/Users/olofs_mba/Documents/Repos/CascadeProjects/windsurf-project/.claude/skills/structlog-logging/SKILL.md</location>
  </skill>
</available_skills>
