# Next Session Instruction Prompt (Template)

Copy-paste this into the next chat to preserve context and enforce repo rules.

---

You are working in the `skriptoteket` repo.

## Product context (MVP)

- Skriptoteket is a teacher-first Script Hub: users log in, browse tools by profession/category, upload files, and get results.
- Roles: users → contributors → admins → superuser.
- Tools can belong to multiple professions/categories (multi-tag).

## Architecture constraints (non-negotiable)

- DDD + Clean Architecture, SRP modules, no god objects, <400–500 LOC per file.
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

## Current code layout

- App code: `src/skriptoteket/`
- DB migrations: `migrations/` + `alembic.ini`
- Run: `pdm run dev`
- Bootstrap superuser: `pdm run bootstrap-superuser`

## Task for this session

<Describe the next concrete task here, e.g. “Implement profession→category navigation UI + DB seed for allowlists”.>

## Acceptance criteria

- Bullets here

---

Start by reading:

1) `.agent/readme-first.md`
2) `docs/index.md`
3) `.agent/rules/000-rule-index.md`
4) `AGENTS.md`
