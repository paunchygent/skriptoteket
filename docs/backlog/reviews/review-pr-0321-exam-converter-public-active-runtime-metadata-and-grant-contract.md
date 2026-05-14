---
type: review
id: REV-PR-0321
title: "Review: PR-0321 Exam Converter public active-runtime metadata and grant contract"
status: approved
owners: "agents"
created: 2026-05-13
updated: 2026-05-13
reviewer: "codex"
prs:
  - PR-0321
adrs:
  - ADR-0085
  - ADR-0079
links:
  - EPIC-21
  - ST-21-03
  - PR-0319
  - REV-PR-0319
  - PR-0320
  - REV-PR-0320
---

# Review: PR-0321 Exam Converter Public Active-Runtime Metadata And Grant Contract

## TL;DR

`PR-0321` is approved as the local metadata/grant bridge required before
`PR-0320` runtime implementation. The bridge keeps general Conversion Hub
authenticated-only, exposes only disabled grant-ready action affordances before
runtime activation, and keeps browser authority to opaque public handles.

## Problem Statement

`REV-PR-0320` found that the public runtime slice cannot proceed unless the
Skriptoteket bridge between upstream public grant authority and local public
metadata is reviewed explicitly. `PR-0321` now owns that bridge.

## Proposed Solution

`PR-0321` adds a governed public runtime-status contract, disabled public action
affordances for the grant-ready state, an explicit browser-safe authority
boundary, OpenAPI/type regeneration, and focused backend/frontend tests.

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/backlog/prs/pr-0321-st-21-03-exam-converter-public-active-runtime-metadata-and-grant-contract.md` | Scope, dependencies, implementation summary, stop conditions | 15 min |
| `src/skriptoteket/domain/curated_apps/models.py` | Runtime-status model and default state | 10 min |
| `src/skriptoteket/infrastructure/curated_apps/registry.py` | `documents.conversion_hub` scoped capability status | 10 min |
| `src/skriptoteket/web/api/v1/public_apps.py` | Public metadata, action affordances, authority boundary | 20 min |
| `frontend/apps/skriptoteket/src/api/openapi.d.ts` and `frontend/apps/skriptoteket/openapi.json` | Generated schema/type shape | 10 min |
| `frontend/apps/skriptoteket/src/views/PublicAppHostView.spec.ts` | Public host grant-ready metadata consumption | 10 min |
| `tests/unit/domain/curated_apps/test_models.py`, `tests/unit/infrastructure/curated_apps/test_registry.py`, `tests/unit/web/test_public_apps_api_routes.py` | Backend contract proof | 15 min |
| `/Users/olofs_mba/Documents/Repos/huleedu/docs/decisions/0045-public-exam-converter-grant-authority-for-sir-convert.md` | Upstream HuleEdu authority | 10 min |
| `/Users/olofs_mba/Documents/Repos/sir-convert-a-lot/docs/backlog/tasks/task-291-define-public-exam-converter-grant-lane-for-digiexam-migration-bundles.md` | Upstream Sir Convert grant lane | 10 min |

**Total estimated time:** ~110 minutes

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Use `contract_only`, `grant_contract_ready`, and `active` as public runtime states | Separates the PR-0319 shell, upstream-contract readiness, and actual PR-0320 runtime availability | [x] |
| Expose grant-ready public action affordances as disabled until runtime is active | Lets the SPA understand the future route contract without submitting work early | [x] |
| Keep browser authority to opaque public handles only | Prevents raw grant, read-lease, signing material, credentials, or direct upstream routes from becoming browser authority | [x] |
| Keep general Conversion Hub `authenticated_only` | Preserves ADR-0085 scoped public exception | [x] |
| Treat Sir Convert `TASK-291` as sufficient upstream acceptance evidence | Sir Convert's own docs contract accepts completed task state as governed backlog authority; `TASK-291` is completed and the converter/auth-profile contracts carry the public-grant verifier shape | [x] |

## Review Checklist

- [x] `PR-0321` status and review state no longer imply approval before this review closes.
- [x] HuleEdu decision references point to the existing `docs/decisions/0045...` path.
- [x] Sir Convert acceptance evidence for `TASK-291` is located or the lack of retained review is kept as a blocker for `PR-0320`.
- [x] Public metadata serializes all three runtime-status states correctly.
- [x] `grant_contract_ready` exposes no enabled submit/poll/result/manifest/download action.
- [x] `active` is the only state that enables runtime action affordances.
- [x] Browser-visible metadata contains no raw `PublicConversionGrantV1`, `PublicArtifactReadLeaseV1`, HuleEdu signing material, Sir Convert credentials, or direct upstream host authority.
- [x] General `/api/v1/public/apps/documents.conversion_hub` remains fail-closed.
- [x] OpenAPI and frontend types reflect the governed metadata shape.
- [x] Focused backend and frontend tests cover the claimed contract.

## Review Feedback

**Reviewer:** `codex`
**Date:** `2026-05-13`
**Verdict:** `approved`

### Required Changes

None.

### Review Notes

- The HuleEdu authority path now points to the real accepted decision:
  `/Users/olofs_mba/Documents/Repos/huleedu/docs/decisions/0045-public-exam-converter-grant-authority-for-sir-convert.md`.
- Sir Convert does not appear to require a separate retained review record for
  every completed task; its `AGENTS.md` requires backlog authority for
  production behavior, and `TASK-291` is `completed` with validation evidence.
  This review therefore accepts completed `TASK-291` plus the updated converter
  and authorization-profile contracts as the upstream Sir Convert approval
  evidence for this bridge.
- The bridge is not runtime activation. It exposes `grant_contract_ready` with
  disabled action affordances, keeps app-wide `documents.conversion_hub`
  `authenticated_only`, and requires `active` before browser-visible runtime
  actions are enabled.
- The eventual `PR-0320` runtime implementation still must prove real
  submit/poll/result/artifact-manifest/download behavior, cookie parity, TTL,
  rate/concurrency controls, fail-closed direct public upstream traffic, no
  account persistence, and no browser-exposed authority material.

### Decision Approvals

- [x] Runtime-status bridge
- [x] Disabled grant-ready action affordances
- [x] Opaque-handle browser authority
- [x] General Conversion Hub remains authenticated-only
- [x] Sir Convert acceptance evidence is sufficient

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | `REV-PR-0321` | Created a retained pending review record so `PR-0321` is no longer a done-but-unreviewed runtime prerequisite. |
| 2 | `REV-PR-0321` | Approved the bridge after verifying HuleEdu path correction, Sir Convert completed-task authority, metadata/action-affordance boundaries, focused tests, lint/typecheck, frontend build, docs gates, and forbidden production-bundle string grep. |
