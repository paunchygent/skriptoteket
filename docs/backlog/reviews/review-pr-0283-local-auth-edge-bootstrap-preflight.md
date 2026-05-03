---
type: review
id: REV-PR-0283
title: "Review: PR-0283 local auth-edge bootstrap preflight"
status: changes_requested
owners: "agents"
created: 2026-05-03
updated: 2026-05-03
reviewer: "lead-developer"
prs:
  - PR-0283
links:
  - EPIC-28
  - ST-28-04
  - PR-0254
  - PR-0260
  - PR-0262
  - PR-0263
  - PR-0280
  - HuleEdu TASK-0325
  - HuleEdu TASK-0380
---

## TL;DR

`PR-0283` has the right auth-edge shape after splitting HuleEdu credential truth
from Skriptoteket projection/RBAC truth, but it must stay blocked until the
provider-side bootstrap account seed authority is concrete and evidenced.

## Problem Statement

Authenticated local browser proof cannot use the retired Skriptoteket
`POST /api/v1/auth/login` endpoint or a local password hash as proof. The review
checks that `.env` bootstrap credentials are verified only by HuleEdu Identity
through Gateway, while Skriptoteket proves only signed-context projection and
local authorization.

## Proposed Solution

Keep `PR-0283` as a narrow Skriptoteket consumer preflight/proof extension that
consumes HuleEdu provider evidence instead of creating or mutating provider
identity state. The retained `PR-0254` proof lane should be extended to cover
both `localhost` and `127.0.0.1` lanes.

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/backlog/prs/pr-0283-st-28-04-local-auth-edge-bootstrap-preflight.md` | Consumer contract, gates, proof shape | 15 min |
| `docs/backlog/stories/story-28-04-cross-app-auth-cutover-smoke-and-operator-runbook-proof.md` | Parent story status and dependency framing | 5 min |
| HuleEdu `TASK-0325` | Local Gateway lane prerequisite | 5 min |
| HuleEdu `TASK-0380` | Provider-owned bootstrap seed-scope authority | 5 min |

**Total estimated time:** ~30 minutes

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Keep HuleEdu as credential authority | Prevents reviving Skriptoteket-local browser passwords. | [x] |
| Keep Skriptoteket as authorization/projection authority | Local RBAC remains app-owned without credential verification shortcuts. | [x] |
| Extend `PR-0254` proof instead of adding a parallel browser proof | Reuses the retained auth-cutover proof lane and avoids duplicate semantics. | [x] |
| Block on HuleEdu `TASK-0380` provider seed evidence | `TASK-0325` proves Gateway lane shape, not the `.env` account seed. | [ ] |

## Review Checklist

- [x] Local password login remains retired.
- [x] `.env` password is never checked against Skriptoteket-local hashes.
- [x] Both loopback lanes are required.
- [x] Key trust parity requires live signed proof or active key/JWKS/fingerprint comparison.
- [x] Public/share route independence remains explicit.
- [x] Legacy local password-owner users fail closed instead of auto-linking.
- [ ] Provider seed authority for `BOOTSTRAP_SUPERUSER_*` has retained evidence.
- [x] Review gate is retained under `docs/backlog/reviews/`.

## Review Feedback

**Reviewer:** lead-developer
**Date:** 2026-05-03
**Verdict:** changes_requested

### Resolved Findings

- Local password contradiction: resolved by splitting HuleEdu credential truth
  from Skriptoteket authorization truth.
- 127 lane: resolved with explicit `localhost` and `127.0.0.1` proof
  requirements.
- Key parity: resolved by requiring signed probe or active key/JWKS/fingerprint
  comparison.
- Playwright duplication: resolved by extending `pr-0254-auth-cutover` instead
  of creating a parallel lane.
- Retained review gate: resolved by this `REV-PR-0283` document.

### Required Changes

1. **Provider seed authority must be concretely evidenced before
   implementation.**

   `PR-0283` now links HuleEdu `TASK-0380` as the provider-owned authority for
   the `browser-bootstrap` Identity seed scope. That fixes the missing
   dependency, but the PR must remain blocked until `TASK-0380` retains the
   exact provider proof artifact consumed by Skriptoteket.

   Required provider evidence:

   - `pdm run run-local-pdm db-lifecycle plan --db identity_db --seed-scope browser-bootstrap`
   - `pdm run run-local-pdm db-lifecycle reset-migrate-seed --db identity_db --seed-scope browser-bootstrap --execute`
   - `pdm run run-local-pdm db-lifecycle verify --db identity_db`
   - local HuleEdu login proof using `BOOTSTRAP_SUPERUSER_EMAIL` and
     `BOOTSTRAP_SUPERUSER_PASSWORD`

   Re-review `PR-0283` after `TASK-0380` is done or after its retained provider
   artifact is available and linked.

### Re-review: Blocked Contract Shape

**Reviewer:** lead-developer
**Date:** 2026-05-03
**Verdict:** approved for the current blocked contract shape; not approved for
implementation.

No new findings. The revised docs now make `PR-0283` `status: blocked`, link
HuleEdu `TASK-0380`, and state that HuleEdu `TASK-0325` is only the local
Gateway-lane authority, not the bootstrap credential seed authority.

The retained `REV-PR-0283` state remains `changes_requested` while provider
evidence is missing. Implementation must wait for HuleEdu `TASK-0380` retained
provider evidence and a later re-review.

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | `PR-0283` | Changed status from `ready` to `blocked`, added `HuleEdu TASK-0380` and `REV-PR-0283`, and named the provider seed-scope commands/evidence consumed by Skriptoteket. |
| 2 | `REV-PR-0283` | Created retained review gate with `changes_requested` status. |
| 3 | `REV-PR-0283` | Recorded the re-review decision: no new findings; blocked contract shape approved while implementation remains gated on HuleEdu `TASK-0380` evidence. |
