---
type: pr
id: PR-0333
title: "ST-21-04 Correction-session backend aggregate and persistence"
status: done
owners: "agents"
created: 2026-05-19
updated: 2026-05-19
stories:
  - "ST-21-04"
tags:
  - backend
  - ddd
  - persistence
  - conversion-hub
  - exam-converter
  - teacher-corrections
dependencies:
  - "ADR-0087"
  - "REV-ST-21-04"
  - "PR-0332"
acceptance_criteria:
  - "Given an authenticated teacher has a local Conversion Hub job, when they create a correction session, then Skriptoteket persists owner-scoped source-bound correction-session state without persisting anything in Sir Convert."
  - "Given an intent is stored, when the aggregate validates it, then it carries the exact producer-issued `source_binding` fields plus item id, sequence, item type, source item fingerprint, correction kind, payload, and session version."
  - "Given a teacher submits a correction for an existing correction target, when the aggregate applies it, then the new intent supersedes the prior active intent and increments the session version."
  - "Given a teacher reverts a correction target, when the aggregate applies the revert, then the active intent is deleted or deactivated and is not included in replay sets."
  - "Given a submitted batch contains duplicate active targets, incompatible answer-key/review-decision state, unsupported kinds, or stale item fingerprints, when validation runs, then persistence fails before any replay/export path can use it."
  - "Given two writes race on the same session, when the caller's expected version is stale, then the application layer reports a `409 Conflict`-class domain error without overwriting the current active set."
  - "Given repository persistence is tested, when sessions and active intents are loaded by owner/job, then cross-owner reads and writes are rejected and active-target constraints are enforced."
---

# PR-0333: ST-21-04 Correction-Session Backend Aggregate And Persistence

## Problem

`ADR-0087` accepts Skriptoteket as the durable owner of authenticated teacher
correction-session truth. The first implementation slice must establish the
domain and persistence contract before any API, replay, or frontend readback
surface can claim saved correction state.

## Scope

- Add the correction-session aggregate and value objects for source-bound
  correction intents.
- Model the current-set invariants from `ADR-0087`: one active intent per
  target, supersession, revert/delete, deterministic replay ordering metadata,
  incompatible active-intent rejection, and optimistic session versioning.
- Add repository protocol and infrastructure persistence for owner-scoped
  sessions and active intents.
- Add migration coverage and focused aggregate/repository tests.

## Non-Goals

- No public API route or OpenAPI export.
- No frontend client or UI integration.
- No Sir Convert replay orchestration.
- No browser proof.
- No matching answer-key persistence before Sir Convert Task 332 and a later
  approved slice.

## Test Plan

- Focused aggregate tests for active-target uniqueness, replace/delete,
  incompatible state, deterministic replay ordering metadata, and stale-version
  conflict behavior.
- Repository and migration tests for owner/job scoping, active-intent
  constraints, persisted source binding, and rollback-safe failures.
- Backend lint/typecheck and focused persistence tests required by the
  Skriptoteket backend skill.

## Implementation Summary

- Added the pure correction-session aggregate, source-binding value object,
  intent target semantics, replacement/revert behavior, deterministic replay
  ordering, and `409 Conflict`-class stale-version domain errors.
- Added PostgreSQL session/intent tables, repository protocol/implementation,
  owner/job scoping through the Conversion Hub job ledger, active-target partial
  unique constraints, and migration idempotency coverage.
- Kept API routes, frontend readback, replay orchestration, browser proof, and
  matching out of scope for the ordered follow-up PRs.

## Verification

- `pdm run test tests/unit/domain/curated_apps/test_exam_converter_correction_sessions.py`
- `pdm run test tests/integration/infrastructure/repositories/test_exam_converter_correction_session_repository.py`
- `pdm run test tests/integration/test_migration_revision_coverage_idempotent.py -k 9b2f4c6d8e10 --override-ini addopts=''`
- `pdm run lint`
- `pdm run typecheck`
