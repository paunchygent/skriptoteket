# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Skriptoteket** (Script Hub) is a teacher-first platform for running curated, upload-based tools. Built with FastAPI (Python 3.13+) and PostgreSQL, using DDD/Clean Architecture with Dishka DI.
UI direction: migrate to a full Vue/Vite SPA (see `docs/adr/adr-0027-full-vue-vite-spa.md`)

Roles hierarchy: **user → contributor → admin → superuser**. Tools are tagged by profession and category. Future: HuleEdu SSO via identity federation (identity external; roles remain local).

## Commands

```bash
# Setup
pdm install -G monorepo-tools
pdm run precommit-install        # REQUIRED: install git hooks

# Database
docker compose up -d db
pdm run db-upgrade              # Apply Alembic migrations
pdm run bootstrap-superuser     # Create first superuser
pdm run provision-user          # Create additional users

# Development
pdm run dev                     # Local server at http://127.0.0.1:8000
pdm run dev-docker              # Server bound to 0.0.0.0 (for Docker)

# Frontend (SPA)
pdm run fe-install              # Install pnpm deps (frontend/)
pdm run fe-dev                  # Vite dev server (SPA)
pdm run fe-build                # SPA production build

# Tool execution (local dev only)
# Add to .env: ARTIFACTS_ROOT=/tmp/skriptoteket/artifacts
mkdir -p /tmp/skriptoteket/artifacts

# Docker compose workflow
pdm run dev-start               # Start with dev overrides
pdm run dev-stop                # Stop containers
pdm run dev-build-start         # Rebuild and start
pdm run dev-build-start-clean   # Full rebuild (no cache)
pdm run dev-db-reset            # Reset database volumes

# Code quality
pdm run format                  # Ruff format
pdm run lint                    # Ruff check + agent-doc budgets + docs contract
pdm run lint-fix                # Auto-fix lint issues
pdm run typecheck               # Mypy
pdm run precommit-run           # REQUIRED: run full pre-commit suite before push

# Testing
pdm run test                    # Run tests (excludes financial/slow/docker)
pdm run test-parallel           # Parallel execution
pytest -k "test_name"           # Single test
pytest tests/unit/              # Unit tests only
pytest tests/integration/       # Integration tests
pytest -m docker                # Docker-dependent tests

# Documentation
pdm run docs-validate           # Validate docs contract

# Session file management (production)
pdm run cleanup-session-files      # Delete expired session dirs (TTL-based)
pdm run clear-all-session-files    # DANGER: delete ALL session files
```

## Architecture

### Layer Structure (`src/skriptoteket/`)

```text
src/skriptoteket/
├── config.py              # Pydantic Settings
├── di.py                  # Dishka container setup
├── protocols/             # ALL Protocol definitions
├── domain/                # Pure business logic (no framework deps)
│   ├── identity/          # User/session models, role guards
│   ├── catalog/           # Tool browsing domain
│   ├── suggestions/       # Script suggestion workflow
│   └── scripting/         # Tool execution domain
├── application/           # Commands/queries + handlers
│   ├── identity/          # Auth handlers
│   ├── catalog/           # Tool listing handlers
│   ├── suggestions/       # Suggestion handlers
│   └── scripting/         # Script execution handlers
├── infrastructure/        # External integrations
│   ├── db/                # SQLAlchemy models, base, UoW
│   ├── repositories/      # PostgreSQL implementations
│   ├── runner/            # Docker script execution
│   └── security/          # Password hashing
├── web/                   # FastAPI (thin layer)
│   ├── app.py             # Application factory
│   ├── pages/             # HTML routes
│   ├── partials/          # HTMX fragments
│   └── templates/         # Jinja2 templates
└── cli/                   # Typer CLI commands
```

### Dependency Flow

```text
web/ ──depends on──▶ application/ ──depends on──▶ domain/
         │                 │                         ▲
         └─────── protocols/ ◀── infrastructure/ ────┘
```

- **Domain**: Zero external dependencies (pure Python + Pydantic)
- **Application**: Depends on protocols, orchestrates use-cases
- **Infrastructure**: Implements protocols (repositories, runners)
- **Web**: Thin routing + template rendering only

### Key Patterns

1. **Protocol-first DI**: All dependencies as `typing.Protocol`; implementations in infrastructure
2. **Unit of Work**: UoW owns commit/rollback; repositories never commit
3. **Command/Query handlers**: One handler per use-case with Pydantic input/output
4. **HTMX partials**: Server-rendered HTML fragments for dynamic UI

## Engineering Rules (Non-Negotiable)

Read `.agent/rules/000-rule-index.md` for the complete rulebook. Key points:

- **No vibe-coding**: Follow established patterns; no makeshift solutions
- **No legacy support**: Full refactor; delete old paths instead of shims
- **Protocol dependencies**: Never depend on concrete implementations
- **Layer boundaries**: Domain is pure; web/api are thin; infrastructure implements protocols
- **Transactions**: Unit of Work owns commit/rollback; repositories never commit
- **Errors**: Raise `DomainError` in domain; map to HTTP in web layer
- **File size**: <400-500 LOC per file (including tests)
- **Pydantic for boundaries**: Use Pydantic models for cross-boundary data; dataclasses only for internal domain structures

## Git Workflow (Non-Negotiable)

- **Never use `git commit --amend`**: Always create fresh commits for fixes discovered after the initial commit
- **Never force push**: If you need to fix something, make a new commit
- This prevents sync issues between local, remote, and deployed servers

## Agent Docs Budgets (Enforced)

- Keep `.agent/readme-first.md` ≤ 300 lines and `.agent/handoff.md` ≤ 200 lines (enforced by pre-commit).
- `.agent/handoff.md` should only keep current sprint-critical backend/frontend info; keep older/completed details in
  `.agent/readme-first.md` (links only) + `docs/`.

## Testing

- **Protocol mocking**: Mock protocols, not implementations
- **Explicit fixtures**: Import from `tests/fixtures/`; no conftest magic
- **Testcontainers**: PostgreSQL integration tests use testcontainers
- **Markers**: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.docker`, `@pytest.mark.slow`, `@pytest.mark.financial`

### Browser Automation

Playwright (recommended), Selenium, Puppeteer available. Run via `pdm run python -m scripts.<module>`.

- **Credentials**: `superuser@local.dev` / `superuser-password`
- **Test tool fixtures**: if a Playwright script needs a specific demo tool/script by slug, add it to the repo script bank
  (`src/skriptoteket/script_bank/`) and seed it (`pdm run seed-script-bank --slug <slug>`; optionally `--sync-code`) before running.

## Documentation Contract

- Contract: `docs/_meta/docs-contract.yaml`
- Templates: `docs/templates/`
- Planning workflow (REQUIRED): `docs/reference/ref-sprint-planning-workflow.md`
- **Review workflow (REQUIRED)**: `docs/reference/ref-review-workflow.md` — all EPICs/ADRs must be reviewed before implementation
- Run `pdm run docs-validate` before committing doc changes
- Agent helpers: `.agent/readme-first.md`, `.agent/handoff.md`

## Tech Stack

- **Frontend (target)**: Vue 3, Vite, Vue Router, Pinia (ADR-0027)
- **Runtime**: Python 3.13+, FastAPI, Uvicorn
- **Database**: PostgreSQL (asyncpg), SQLAlchemy 2.x (async), Alembic
- **DI**: Dishka (protocol-first)
- **Security**: Argon2 password hashing
- **Testing**: pytest, pytest-asyncio, testcontainers, httpx
- **Quality**: Ruff (100 char lines), Mypy

## Home Server Deployment

**CRITICAL**: Production deployments use `compose.prod.yaml`, NOT `compose.yaml`.

### SSH Access

```bash
ssh hemma              # Via hemma.hule.education (works everywhere)
ssh hemma-local        # Via 192.168.0.9 (local network, faster)
```

### Standard Deploy

```bash
ssh hemma "cd ~/apps/skriptoteket && git pull && docker compose -f compose.prod.yaml up -d --build"
```

### Deploy with Migrations

```bash
ssh hemma "cd ~/apps/skriptoteket && git pull && docker compose -f compose.prod.yaml up -d --build"
ssh hemma "docker exec skriptoteket-web pdm run db-upgrade"
```

### CLI Commands in Container

Always use `-e PYTHONPATH=/app/src` for CLI commands:

```bash
ssh hemma "docker exec -e PYTHONPATH=/app/src skriptoteket-web pdm run python -m skriptoteket.cli <command>"
```

### Key Differences: compose.yaml vs compose.prod.yaml

| Feature | compose.yaml (dev) | compose.prod.yaml (prod) |
|---------|-------------------|--------------------------|
| Database | Local `skriptoteket-db-1` | Shared `shared-postgres` |
| Docker socket | Not mounted | Mounted (for runner) |
| Artifacts | Not mounted | Persistent volume |
| Network | `skriptoteket_default` | `hule-network` |
| Proxy headers | Manual | Built-in |

### Reverse Proxy (nginx-proxy + acme-companion)

Infrastructure runs in `~/infrastructure/` with auto-SSL via Let's Encrypt:

| Service | Image | Purpose |
|---------|-------|---------|
| `nginx-proxy` | `nginxproxy/nginx-proxy:1.6` | Auto-discovers containers via `VIRTUAL_HOST` |
| `acme-companion` | `nginxproxy/acme-companion:2.4` | Auto SSL certificate management |

**Public URLs:**
- https://skriptoteket.hule.education (main app)
- https://grafana.hemma.hule.education (admin / `GRAFANA_ADMIN_PASSWORD`)
- https://prometheus.hemma.hule.education (admin / `PROMETHEUS_BASIC_AUTH_PASSWORD`)

**Credentials** stored in `~/apps/skriptoteket/.env` on server. Reset Grafana password:
```bash
ssh hemma "docker exec grafana grafana cli admin reset-admin-password '<password>'"
```

### Scheduled Jobs

| Timer | Service | Schedule | Description |
|-------|---------|----------|-------------|
| `skriptoteket-session-files-cleanup.timer` | `skriptoteket-session-files-cleanup.service` | Hourly | TTL cleanup of expired session files |

```bash
# Check timer status
ssh hemma "systemctl list-timers | grep skriptoteket"

# View cleanup logs
ssh hemma "journalctl -u skriptoteket-session-files-cleanup.service -n 50 --no-pager"

# Manual cleanup run
ssh hemma "sudo systemctl start skriptoteket-session-files-cleanup.service"
```

### AI Inference Infrastructure

| Service      | Port | Purpose                                  |
|--------------|------|------------------------------------------|
| llama-server | 8082 | ROCm GPU inference (Qwen3-Coder-30B-A3B) |
| tabby        | 8083 | Code completion API (`/v1/completions`)  |

```bash
ssh hemma "curl -s http://localhost:8083/v1/health | jq .model"  # → "Remote"
```

Runbooks: `docs/runbooks/runbook-gpu-ai-workloads.md`, `docs/runbooks/runbook-tabby-codemirror.md`

### Runbooks

See `docs/runbooks/runbook-home-server.md` for detailed operations.

**Note**: Runbooks (`docs/runbooks/`) and rules (`.agent/rules/`) are gitignored because they may contain sensitive
information (credentials, internal IPs, etc.). These files are local-only and should not be committed.
