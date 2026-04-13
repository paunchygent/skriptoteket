---
type: review
id: REV-PR-0264
title: "Review: PR-0264 auth outcome observability for HuleEdu cutover"
status: pending
owners: "agents"
created: 2026-04-13
updated: 2026-04-13
reviewer: "lead-developer"
prs:
  - PR-0264
adrs:
  - ADR-0018
  - ADR-0019
  - ADR-0026
  - ADR-0083
links:
  - EPIC-28
  - ST-28-10
  - PR-0254
  - PR-0263
---

## TL;DR

Review the first Skriptoteket-owned auth outcome observability slice after the cross-app cutover
proof. The core question is whether `PR-0264` makes signed-context, projection, provisioning, and
local RBAC outcomes visible without reintroducing local browser-session ownership or leaking
identity data.

## Problem Statement

`PR-0254` and `PR-0263` certify that the auth cutover path works on both loopback lanes. Operators
now need to diagnose what happened when that path fails. A naive metrics pass could undo the
cutover boundary by recreating local session gauges, over-labeling subjects/emails, or pretending
Skriptoteket owns Gateway/session/lifecycle telemetry.

## Proposed Solution

Approve a narrow implementation slice that adds sanitized, low-cardinality observability for the
Skriptoteket-owned side of the cutover:

- signed internal identity verification at the app boundary
- realm-aware projection and provisioning outcomes
- local `User.role` RBAC denial decisions
- consumer-side runbook correlation back to HuleEdu Gateway/session signals

HuleEdu-owned browser session, product realm ceremony selection, provider lifecycle, CSRF
authority, and logout authority remain upstream observability responsibilities.

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/backlog/prs/pr-0264-st-28-10-auth-outcome-observability-for-huleedu-cutover.md` | Scope, metric/log contract, ownership split | 20 min |
| `docs/backlog/stories/story-28-10-auth-outcome-observability-for-realm-cutover.md` | Parent story acceptance criteria | 5 min |
| `docs/backlog/epics/epic-28-skriptoteket-auth-authority-cutover-to-huleedu.md` | Auth cutover sequence and final proof context | 8 min |
| `docs/runbooks/runbook-observability-logging.md` | Current log/correlation policy | 5 min |
| `docs/runbooks/runbook-observability-metrics.md` | Current metrics and retired auth metric policy | 5 min |
| `docs/runbooks/runbook-observability-tracing.md` | Optional trace correlation expectations | 3 min |

**Total estimated time:** ~46 minutes

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Keep HuleEdu Gateway/session/lifecycle observability upstream-owned | Prevents Skriptoteket from recreating auth authority | [ ] |
| Add Skriptoteket-owned auth outcome counters/logs only at app-continuation, projection, and RBAC boundaries | Keeps the first slice diagnosable and bounded | [ ] |
| Use bounded enum-like metric labels and sanitized structured log fields | Prevents high cardinality and identity leakage | [ ] |
| Prefer a small protocol-first recorder over scattered logger/metric calls | Keeps tests behavior-focused and preserves clean architecture boundaries | [ ] |
| Update runbooks with correlation handoff across HuleEdu Gateway and Skriptoteket | Makes the signal usable in normal operations | [ ] |

## Review Checklist

- [ ] Scope is bounded to `ST-28-10` and does not reopen auth behavior.
- [ ] No metric recreates `skriptoteket_active_sessions` or local browser-session state.
- [ ] Proposed labels cannot contain user ids, raw realm subjects, emails, raw URLs, tokens,
      signed headers, CSRF values, or exception text.
- [ ] HuleEdu-owned Gateway/session/lifecycle outcomes are separated from Skriptoteket-owned
      app-continuation/projection/RBAC outcomes.
- [ ] The planned recorder shape preserves protocol-first DI and keeps domain code pure.
- [ ] Tests assert behavior and redaction without patching implementation-private dependencies.
- [ ] Runbook requirements include correlation-id handoff and failure interpretation.

## Review Feedback

**Reviewer:** lead-developer
**Date:** 2026-04-13
**Verdict:** pending

### Required Changes

Pending review.

### Suggestions (Optional)

Pending review.

### Decision Approvals

- [ ] HuleEdu ownership split
- [ ] Skriptoteket-owned signal boundaries
- [ ] Bounded labels and sanitized logs
- [ ] Protocol-first recorder
- [ ] Correlation handoff runbook

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | `PR-0264` | Created the review-ready auth outcome observability slice for `ST-28-10`. |
| 2 | `REV-PR-0264` | Created the retained review gate that must approve the signal contract before implementation. |
