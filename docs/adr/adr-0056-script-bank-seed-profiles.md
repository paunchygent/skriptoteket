---
type: adr
id: ADR-0056
title: "Script bank seeding profiles (curated vs test)"
status: proposed
owners: "agents"
deciders: ["user-lead"]
created: 2026-01-12
---

## Context

Script bank seeding currently uses a single repo list. That makes it easy to seed demo/test tools into production,
even when we only want curated tools to exist in the shared production database. We also want dev/staging to continue
seeding both curated and test/demo tools for verification and E2E coverage.

## Decision

- Add a `seed_group` attribute to `ScriptBankEntry` with allowed values:
  - `curated` (production-eligible tools)
  - `test` (development/staging tools only)
- Extend `seed-script-bank` with a `--profile` flag:
  - `dev` → seeds `curated` + `test`
  - `prod` → seeds `curated` only
- Allow an explicit `--group` override for targeted seeding (e.g., `--group curated` or `--group test`).

## Consequences

- Script bank entries must be tagged with `seed_group`.
- Home-server runbook uses `--profile prod` to prevent seeding test tools into shared Postgres.
- Dev/staging runbooks use `--profile dev`.
