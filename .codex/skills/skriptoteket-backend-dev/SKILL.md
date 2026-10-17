---
name: skriptoteket-backend-dev
description: "Backend engineering for Skriptoteket (FastAPI monolith): architecture + file tree navigation (DDD/Clean layers), protocol-first DI, Unit of Work + transactions, DomainError semantics, core data shapes/contracts (tool UI contract v2, runner contracts, file refs), and backend testing strategy. Use when implementing/refactoring/reviewing backend code; use local-devops for local dev setup and troubleshooting."
---

# Skriptoteket backend dev

## Development Runtime

Use `local-devops` and its Skriptoteket reference for the current stack,
bootstrap, logs, and health commands. Use `staging-walk` for protected browser
proof; host-only backend iteration does not establish that proof.

## File tree + entrypoints (codemap)

- App factory: `src/skriptoteket/web/app.py` (FastAPI app, middleware order, Dishka wiring)
- Composition root: `src/skriptoteket/di/__init__.py` (providers assembled)
- API surface: `src/skriptoteket/web/api/v1/` (thin routers + boundary DTOs)
- Domain: `src/skriptoteket/domain/` (pure rules; no FastAPI/SQLAlchemy)
- Application: `src/skriptoteket/application/` (command/query handlers; orchestrates UoW + protocols)
- Protocols: `src/skriptoteket/protocols/` (typing.Protocol boundaries)
- Infrastructure: `src/skriptoteket/infrastructure/` (DB/repos, runner, llm, integrations)
- Worker loop: `src/skriptoteket/workers/execution_queue_worker.py` (ADR-0062)
- Runner runtime: `src/skriptoteket/infrastructure/runner/` + `runner/` (sandboxed execution env)
- DB migrations: `migrations/` + `alembic.ini`

Tip: generate a fresh tree with `find src/skriptoteket -maxdepth 2 -type d`.

## Topic Contracts

Read [backend-contracts.md](references/backend-contracts.md) when changing HTTP
or browser-trust boundaries, DI/persistence, curated-app APIs, editor AI,
execution queues, or Python implementation conventions. Migration proof and
revision immutability belong to the testing skill's migration reference.

## Critical invariants (non-negotiable)

- Keep domain pure: no web/db/framework imports in `src/skriptoteket/domain/**`.
- Keep web/api thin: validate + call handlers; never put business logic in routers.
- Raise `DomainError` (no HTTP) and map to HTTP in `src/skriptoteket/web/*`.
- Unit of Work owns commit/rollback; repositories never commit (see `src/skriptoteket/infrastructure/db/uow.py`).
- Preserve OpenAPI-safe router typing; follow the HTTP contracts in the routed reference.
- For editor AI / LLM changes: follow `docs/runbooks/run-skript-runbook-openai-responses-api-prompt-caching-runbook-openai-responses-api-prompt-caching.md`.
- For execution queue/worker changes: follow `docs/decisions/adr-skript-0062-execution-queue-and-worker-loop-postgres.md`.

## Key ADRs + “goal state” watchlist

Read first when touching these areas:

- Architecture + boundaries: `docs/decisions/adr-skript-0004-architecture-ddd-clean-architecture-di-async-srp.md`
- Browser-session authority: `docs/decisions/adr-skript-0076-huleedu-owned-browser-session-authority-for-skriptoteket.md`
- Local roles: `docs/decisions/adr-skript-0005-user-roles-and-script-governance-rbac.md`
- Tool UI contract v2: `docs/decisions/adr-skript-0022-tool-ui-contract-v2-typed-outputs-actions-and-state.md` (models in `src/skriptoteket/domain/scripting/ui/contract_v2.py`)
- Tool sessions + persistence: `docs/decisions/adr-skript-0024-tool-sessions-and-ui-payload-persistence.md`
- Multi-file inputs: `docs/decisions/adr-skript-0031-multi-file-input-contract.md`
- Execution queue worker loop: `docs/decisions/adr-skript-0062-execution-queue-and-worker-loop-postgres.md`
- OpenAPI as source + frontend types: `docs/decisions/adr-skript-0030-openapi-as-the-api-source-of-truth-generated-typescript-types.md`
- Runner request envelope v1: `docs/decisions/adr-skript-0063-runner-request-envelope-v1-request-json.md`
- File references + resolver: `docs/decisions/adr-skript-0064-file-references-fileref-resolver-staging-manifest.md`

For roadmap/critical-path work, start from the active backlog through
`docs/index.md`.

## Stories + planning workflow (when implementing backlog work)

- Planning workflow: `docs/index.md`
- Review gate (required for proposed EPICs/ADRs): `agent-docs-governance`

## DB + migrations

- Migrations live in `migrations/versions/`; workflow in `.codex/skills/skriptoteket-testing/references/migrations.md`.
- Upgrade dev DB: `pdm run db-upgrade`
- If you add a migration, add/run the docker idempotency integration test (see `.codex/skills/skriptoteket-testing/references/migrations.md`).

## CLIs + seeding

- Bootstrap superuser: `pdm run bootstrap-superuser`
- Seed script bank:
  - Runbook: `docs/runbooks/run-skript-runbook-script-bank-seeding-repo-db-runbook-script-bank-seeding-repo-db.md`
  - Safe default: `pdm run seed-script-bank --dry-run --profile dev`
- Execution worker (one-off): `PYTHONPATH=src pdm run python -m skriptoteket.cli run-execution-worker --once`

## Harnesses (debugging / regression checks)

- OpenAPI export: `pdm run openapi-export-v1`
- Frontend API types: `pdm run fe-gen-api-types`
- Use the shared staging-walk skill for staging and browser proof on Hemma.
- Edit-ops harnesses (ad-hoc): `python -m scripts.edit_ops_harness` and `python -m scripts.chat_edit_ops_context_probe`

## Auth and API proof boundary

Use the shared staging-walk skill for staging and browser proof on Hemma.

- Direct Skriptoteket backend calls are for unit tests, integration tests, public routes, health checks, and explicitly scoped backend probes.
- Correlation header: `X-Correlation-ID: <uuid>` (echoed by middleware).

## Testing protocol (backend)

- Follow `.codex/skills/skriptoteket-testing/SKILL.md` and `docs/runbooks/run-skript-runbook-testing-pytest-vitest-playwright-runbook-testing-pytest-vitest-playwright.md`.
- Default: `pdm run test` (unit tests mock protocols; integration uses Docker/testcontainers).
- Also run: `pdm run lint` and `pdm run typecheck` for backend changes.
