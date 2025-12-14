# Next Session Instruction Prompt (Template)

Use this when you need to (a) start a new session or (b) provide a “message to a new developer/agent”.

Rules:

- Address the recipient as **you** (second person).
- Include file references and commands; do not assume the reader saw prior chat context.
- Do not include secrets/tokens/passwords.

---

Role: You are the lead developer and architect of Skriptoteket.

You are working in the `skriptoteket` repo.

## Product context (MVP)

- Skriptoteket is a teacher-first Script Hub: users log in, browse tools by profession/category, upload files, and get results.
- Roles: users → contributors → admins → superuser.
- Tools can belong to multiple professions/categories (multi-tag).

## Architecture constraints (non-negotiable)

- DDD + Clean Architecture, SRP modules, no god objects, <400–500 LOC per file.
- No legacy support/workarounds: do full refactor; delete old paths instead of shims.
- Protocol-first DI: domain/application must not depend on frameworks or concrete implementations.
- Async-first, single container; PostgreSQL repositories behind protocols; UoW controls transactions.
- Pydantic models cross boundaries; dataclasses only within a single domain.

## Identity constraints (v0.1 + future)

- v0.1: local accounts (admin-provisioned), password auth, server-side sessions in PostgreSQL.
- Login is required for browsing/running.
- Future: HuleEdu SSO via identity federation; roles remain local to Skriptoteket.
- User model must support `external_id` (nullable) and `auth_provider` (e.g., `local`, future `huleedu`).

## Docs governance

- Follow `docs/_meta/docs-contract.yaml` and templates under `docs/templates/`.
- Do not create new `docs/<top>/` folders without updating the contract.
- Run `pdm run docs-validate` for docs changes.

## Key docs to read (source of truth)

- `docs/index.md`
- `docs/prd/prd-script-hub-v0.1.md`
- ADRs: `docs/adr/` (notably `adr-0004-clean-architecture-ddd-di.md`, `adr-0009-auth-local-sessions-admin-provisioned.md`, `adr-0011-huleedu-identity-federation.md`)
- Rules: `.agent/rules/000-rule-index.md`

## Current code layout

- App code: `src/skriptoteket/`
- DB migrations: `migrations/` + `alembic.ini`
- Run: `pdm run dev`
- Bootstrap superuser: `pdm run bootstrap-superuser`

## Task for this session

Pick up from `main` and implement ST-03-02 “Admin reviews suggestions (accept/modify/deny)” end-to-end (domain →
application → infra → web), continuing from the existing ST-03-01 foundation.

Entry points:

- Story: `docs/backlog/stories/story-03-02-admin-review-and-decision.md`
- Epic: `docs/backlog/epics/epic-03-script-governance-workflow.md`
- Existing suggestion submission + queue:
  - Domain: `src/skriptoteket/domain/suggestions/models.py`
  - Application: `src/skriptoteket/application/suggestions/`
  - Protocols: `src/skriptoteket/protocols/suggestions.py`
  - Infra: `src/skriptoteket/infrastructure/repositories/script_suggestion_repository.py`, `migrations/versions/0003_script_suggestions.py`
  - Web: `src/skriptoteket/web/pages/suggestions.py` (routes `/suggestions/new`, `/admin/suggestions`)

## Acceptance criteria

- Docs: set ST-03-02 → `in_progress` at start; mark `done` when AC is met (keep EPIC-03 `active`).
- Domain: introduce a review/decision model and invariants (no HTTP concerns; raise `DomainError` only).
- Application: admin-only decision handler(s) that record decision + rationale and link to suggestion.
- On accept: create a draft Tool entry and link it to the suggestion (not runnable/published yet).
- Infra: add migrations + SQLAlchemy models/repos; keep UoW-owned commit/rollback (repos never commit).
- Web: add minimal admin UI to open a suggestion and submit accept/modify/deny (role-gated).
- Tests: protocol-mocked unit tests for handlers + REQUIRED Testcontainers migration idempotency test.
- Session rule: run the app and verify the pages render/flow works; write exact steps in `.agent/handoff.md`.
- End of session: update docs + `.agent/handoff.md`, then produce a new “next session” instruction for your successor.

---

Start by reading:

1) `.agent/readme-first.md`
2) `docs/index.md`
3) `.agent/rules/000-rule-index.md`
4) `AGENTS.md`
