---
type: review
id: REV-PR-0254
title: "Review: PR-0254 cross-app auth cutover smoke and runbook proof"
status: approved
owners: "agents"
created: 2026-04-13
updated: 2026-04-13
reviewer: "lead-developer"
prs:
  - PR-0254
links:
  - EPIC-28
  - ST-28-04
  - ST-28-11
  - ST-28-12
  - PR-0260
  - PR-0261
  - PR-0262
  - HuleEdu TASK-0325
  - HuleEdu TASK-0326
  - HuleEdu TASK-0327
---

## TL;DR

Review the final cross-app proof slice after the new bootstrap and lifecycle
prerequisites are accepted.

## Problem Statement

`PR-0254` is no longer just a smoke test over the current login entry. It must
consume provider Gateway proof, HuleEdu bootstrap identities, Skriptoteket local
projection/role bootstrap, and real standalone lifecycle proof before certifying
the cutover.

## Proposed Solution

Keep `PR-0254` as the final operator proof, but gate it behind HuleEdu
`TASK-0325`, `TASK-0326`, `TASK-0327`, and Skriptoteket `PR-0260` through
`PR-0262`.

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/backlog/prs/pr-0254-st-28-04-cross-app-auth-cutover-smoke-and-runbook-proof.md` | Final smoke contract | 10 min |
| `docs/backlog/stories/story-28-04-cross-app-auth-cutover-smoke-and-operator-runbook-proof.md` | Parent story expectations | 5 min |
| `PR-0260` through `PR-0262` | Prerequisite proof lanes | 10 min |

**Total estimated time:** ~25 minutes

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Gate final proof behind bootstrap/lifecycle slices | Avoid certifying a partial login-only path | [x] |
| Keep HuleEdu and Skriptoteket repo responsibilities separate | Provider identity lifecycle and consumer projection roles are different contracts | [x] |
| Require direct-action link proof | Deliberate clicks and email links must land on the requested action page, not a generic HuleEdu page | [x] |
| Require sanitized operator evidence | Final proof should be auditable without leaking secrets | [x] |

## Review Checklist

- [x] `PR-0254` depends on the correct HuleEdu and Skriptoteket prerequisites
- [x] Final proof includes role matrix, lifecycle, projection, and local RBAC
- [x] Final proof includes direct-action landing for login/register/forgot/verify/reset links
- [x] Runbook proof covers both local and production-relevant lanes
- [x] Unsupported realms are reported as blocked, not silently passed
- [x] Sanitized evidence is required

## Review Feedback

**Reviewer:** lead-developer
**Date:** 2026-04-13
**Verdict:** `approved`

### Required Changes

None. `PR-0254` correctly remains the final proof gate and now depends on the provider Gateway,
bootstrap identity, standalone lifecycle, Skriptoteket projection/role bootstrap, direct-action
landing, and sanitized evidence lanes before final certification.

### Suggestions (Optional)

Keep `REV-PR-0260`, `REV-PR-0261`, and `REV-PR-0262` visible as separate gates. This approval
accepts the `PR-0254` planning contract; it does not collapse or pre-approve the prerequisite
implementation/review lanes.

### Decision Approvals

- [x] Bootstrap/lifecycle gating
- [x] Correct repo ownership
- [x] Direct-action link proof
- [x] Sanitized final evidence

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | `PR-0254` | Retained review gate for final cross-app proof |
| 2 | `REV-PR-0254` | Approved after confirming the final proof remains gated behind HuleEdu `TASK-0325` through `TASK-0327` and Skriptoteket `PR-0260` through `PR-0262` |

## Dependency Update 2026-04-13

HuleEdu `TASK-0326` is now done and deployed at merge commit `92419293`, which
unblocks Skriptoteket `PR-0260`. This does not pull `PR-0254` forward:
`PR-0254` still waits for `PR-0260`, HuleEdu `TASK-0327`, `PR-0261`, and
`PR-0262`.
