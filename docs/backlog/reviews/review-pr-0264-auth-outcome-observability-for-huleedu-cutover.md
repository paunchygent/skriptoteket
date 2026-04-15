---
type: review
id: REV-PR-0264
title: "Review: PR-0264 auth outcome observability for HuleEdu cutover"
status: approved
owners: "agents"
created: 2026-04-13
updated: 2026-04-15
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
| Keep HuleEdu Gateway/session/lifecycle observability upstream-owned | Prevents Skriptoteket from recreating auth authority | [x] |
| Add Skriptoteket-owned auth outcome counters/logs only at app-continuation, projection, and RBAC boundaries | Keeps the first slice diagnosable and bounded | [x] |
| Use bounded enum-like metric labels and sanitized structured log fields | Prevents high cardinality and identity leakage | [x] |
| Prefer a small protocol-first recorder over scattered logger/metric calls | Keeps tests behavior-focused and preserves clean architecture boundaries | [x] |
| Update runbooks with correlation handoff across HuleEdu Gateway and Skriptoteket | Makes the signal usable in normal operations | [x] |

## Review Checklist

- [x] Scope is bounded to `ST-28-10` and does not reopen auth behavior.
- [x] No metric recreates `skriptoteket_active_sessions` or local browser-session state.
- [x] Proposed labels cannot contain user ids, raw realm subjects, emails, raw URLs, tokens,
      signed headers, CSRF values, or exception text.
- [x] HuleEdu-owned Gateway/session/lifecycle outcomes are separated from Skriptoteket-owned
      app-continuation/projection/RBAC outcomes.
- [x] The planned recorder shape preserves protocol-first DI and keeps domain code pure.
- [x] Tests assert behavior and redaction without patching implementation-private dependencies.
- [x] Runbook requirements include correlation-id handoff and failure interpretation.

## Review Feedback

**Reviewer:** lead-developer
**Date:** 2026-04-15
**Initial Verdict:** approved
**Implementation Follow-up Verdict:** approved on re-review 2026-04-15.

### Required Changes

- Addressed 2026-04-15: RBAC observability must cover non-dependency local RBAC denials as
  well as `require_app_*` dependency denials. RBAC recording now happens at the central web
  `DomainError` boundary, and eval-mode plus draft-lock force-takeover role denials use role guard
  metadata so they emit bounded `required_role` / `actual_role` labels and `auth.rbac.denied`.
- Addressed 2026-04-15: new auth observability code must avoid `Any` and `cast(...)`.
  The recorder now uses a logger protocol, the error boundary uses a request-container protocol,
  and Prometheus duplicate-registration recovery uses typed collector helpers.
- Final re-review 2026-04-15: no required changes remain. `PR-0264` can stay `done`, and
  `ST-28-10` / `EPIC-28` remain justified as done because the auth cutover now has bounded
  Skriptoteket-owned observability without restoring local browser-session ownership.

### Suggestions (Optional)

- Keep the first implementation focused on counters, structured logs, and runbook triage.
- Defer dashboards/alerts until real auth outcome rates exist after launch proof.

### Decision Approvals

- [x] HuleEdu ownership split
- [x] Skriptoteket-owned signal boundaries
- [x] Bounded labels and sanitized logs
- [x] Protocol-first recorder
- [x] Correlation handoff runbook

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | `PR-0264` | Created the review-ready auth outcome observability slice for `ST-28-10`. |
| 2 | `REV-PR-0264` | Created the retained review gate that must approve the signal contract before implementation. |
| 3 | `REV-PR-0264` | Approved the bounded signal contract for implementation after lead-architect/CTO review. |
| 4 | `REV-PR-0264` | Recorded the implementation follow-up `changes_requested` decision: dependency-only RBAC observability was too narrow. |
| 5 | `PR-0264` | Resolved the follow-up by centralizing RBAC denial recording in the web `DomainError` boundary and adding non-dependency RBAC tests. |
| 6 | `PR-0264` | Addressed the latest `changes_requested` findings by routing eval-mode and force-takeover role denials through role guards, adding direct-route/application-handler regression checks, and replacing new `Any` / `cast(...)` usage with protocols and typed helpers. |
| 7 | `REV-PR-0264` | Re-reviewed the latest fixes and approved the retained implementation record; downstream `PR-0264`, `ST-28-10`, and `EPIC-28` done statuses remain valid. |
