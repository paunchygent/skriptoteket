---
type: review
id: REV-EPIC-28
title: "Review: Skriptoteket auth authority cutover to HuleEdu"
status: pending
owners: "agents"
created: 2026-03-28
reviewer: "lead-developer"
epic: EPIC-28
adrs:
  - ADR-0076
stories:
  - ST-28-01
  - ST-28-02
  - ST-28-03
  - ST-28-04
---

## TL;DR

EPIC-28 proposes a hard-break cutover where Skriptoteket stops owning browser auth locally and
instead consumes a HuleEdu-owned cookie-session + CSRF browser contract through
`https://api.hule.education`. The package preserves Skriptoteket's richer bootstrap semantics and
dedicated redirect-preserving auth-entry UX, explicitly rejects bearer-browser auth and app-local auth bridges, and adds a
cross-app smoke lane as the acceptance proof.

## Problem Statement

Skriptoteket already depends on stronger browser-session semantics than HuleEdu's current
bearer-in-frontend model provides: cookie auth, CSRF, rich bootstrap state, and redirect-preserving
login handoffs. A real cross-app cutover cannot succeed by downgrading Skriptoteket to bearer-browser
auth or by keeping two browser contracts alive. We need one final shared browser-session contract
that HuleEdu owns and Skriptoteket can safely adopt.

## Proposed Solution

- Add ADR-0076 to define the target browser contract:
  - HuleEdu Identity owns session authority
  - HuleEdu Gateway is the only browser auth edge
  - browser auth uses secure cookies + CSRF
  - canonical bootstrap moves to `GET /v1/auth/session`
  - no bearer-browser end state and no local Skriptoteket bridge
- Add a proposed epic with four ready stories:
  - frontend auth store/API client cutover
  - dedicated auth-entry route/route-handoff preservation
  - deletion of local browser-auth ownership
  - cross-app smoke + runbook proof

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/adr/adr-0076-huleedu-owned-browser-session-authority-for-skriptoteket.md` | Final browser-session contract and rejected options | 8 min |
| `docs/backlog/epics/epic-28-skriptoteket-auth-authority-cutover-to-huleedu.md` | Scope, hard-break posture, sequencing | 6 min |
| `docs/backlog/stories/story-28-01-frontend-auth-store-and-api-client-cutover-to-huleedu-session-contract.md` | Bootstrap + CSRF cutover | 5 min |
| `docs/backlog/stories/story-28-02-auth-interruption-and-protected-route-handoff-on-huleedu-owned-session.md` | UX parity, dedicated auth-entry interruption, and return-to-origin guarantees | 5 min |
| `docs/backlog/stories/story-28-03-remove-local-auth-ownership-and-regenerate-client-contracts.md` | Deletion posture and contract cleanup | 5 min |
| `docs/backlog/stories/story-28-04-cross-app-auth-cutover-smoke-and-operator-runbook-proof.md` | Joint proof and operator verification | 5 min |

**Total estimated time:** ~34 minutes

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Use `GET /v1/auth/session` as the canonical browser bootstrap instead of keeping `/v1/auth/me` as the browser contract | Cleaner long-term session semantics and an explicit hard break | [ ] |
| Keep browser auth on secure cookies + CSRF instead of bearer tokens in frontend storage | Preserves the stronger Skriptoteket-grade browser contract needed for SaaS and cross-app parity | [ ] |
| Use `https://api.hule.education` as the browser auth origin for both apps | One real authority, no app-local auth ownership | [ ] |
| Reject a Skriptoteket-local auth bridge | Prevents a hidden dual-contract end state | [ ] |
| Preserve dedicated `/auth/login` handoff and redirect semantics as a non-regression requirement | The auth authority changes, but the Skriptoteket UX contract should not regress | [ ] |

## Review Checklist

- [ ] ADR-0076 defines one final browser auth contract with clear ownership boundaries
- [ ] EPIC-28 scope is appropriately hard-break and does not hide a compatibility bridge
- [ ] Stories preserve Skriptoteket's richer bootstrap and dedicated auth-entry UX
- [ ] The package explicitly rejects bearer-browser and dual-contract end states
- [ ] Risks and external HuleEdu dependencies are identified clearly

## Review Feedback

**Reviewer:** @lead-developer
**Date:** 2026-03-28
**Verdict:** pending

### Required Changes

- Pending review.

### Suggestions (Optional)

- None yet.

### Decision Approvals

- [ ] Use `GET /v1/auth/session` as the canonical browser bootstrap
- [ ] Keep cookie-session + CSRF as the browser transport
- [ ] Use `https://api.hule.education` as the browser auth origin
- [ ] Reject a Skriptoteket-local auth bridge
- [ ] Preserve dedicated `/auth/login` handoff and expiry recovery UX

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | ADR-0076 | Drafted the HuleEdu-owned browser-session target for Skriptoteket |
| 2 | EPIC-28 | Drafted the hard-break cutover epic and sequencing |
| 3 | ST-28-01..04 | Drafted the frontend cutover, dedicated auth-entry handoff, deletion, and proof slices |
