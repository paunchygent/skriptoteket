---
type: review
id: REV-EPIC-02
title: "Review: Local password reset via emailed token"
status: approved
owners: "agents"
created: 2026-03-30
reviewer: "lead-developer"
epic: EPIC-02
adrs:
  - ADR-0078
stories:
  - ST-02-07
---

## TL;DR

This slice adds self-service password recovery for local Skriptoteket accounts by introducing a
dedicated reset-token flow, generic account-enumeration-safe request semantics, and forced session
revocation after a successful reset. It explicitly keeps federated/HuleEdu identities out of scope
and reuses the existing local auth/email stack instead of introducing a new auth mechanism.

## Problem Statement

Forgotten local passwords still require manual operator intervention and the current runbook points
at direct database hash replacement as the routine fallback. That is not acceptable for a
teacher-facing self-service product and it leaves the auth stack without a standard recovery path.

## Proposed Solution

- Add ADR-0078 to define the reset-token model and security posture.
- Extend EPIC-02 with a ready story and planning slice for local password reset.
- Add a dedicated `password_reset_tokens` seam rather than repurposing email-verification tokens.
- Add anonymous request/reset endpoints with generic success on request.
- Revoke all active sessions and clear lockout state after successful reset.
- Add unauthenticated forgot/reset SPA routes using the existing verification flow as the UX
  baseline.

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/adr/adr-0078-local-password-reset-via-emailed-token.md` | Token lifecycle, session revocation, and local-only boundary | 8 min |
| `docs/backlog/epics/epic-02-identity-and-access-control.md` | Epic scope alignment and auth-doc drift cleanup | 4 min |
| `docs/backlog/stories/story-02-07-local-password-reset-via-emailed-token.md` | Acceptance criteria, slice boundaries, and verification expectations | 5 min |
| `docs/backlog/prs/pr-0172-local-password-reset-via-emailed-token.md` | Implementation sequencing and non-goals | 5 min |

**Total estimated time:** ~22 minutes

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Use a dedicated `password_reset_tokens` table instead of a generic shared email-action token table | Keeps semantics explicit and lowers implementation risk for the first recovery slice | [x] |
| Return generic success from `forgot-password` for unknown, inactive, unverified, and federated accounts | Prevents account-state disclosure at the public request endpoint | [x] |
| Revoke all active sessions and clear lockout state after successful reset | Makes reset a clear recovery/security boundary instead of just a hash swap | [x] |
| Restrict the flow to `AuthProvider.LOCAL` accounts | Preserves the future HuleEdu identity boundary and avoids a hidden dual-auth fallback | [x] |
| Require explicit login after reset instead of auto-login | Keeps the recovery flow simple and avoids adding a new anonymous-to-session elevation path | [x] |

## Review Checklist

- [x] ADR-0078 defines a clear reset-token contract and local-only boundary
- [x] EPIC-02 scope stays appropriately narrow for identity recovery
- [x] ST-02-07 acceptance criteria are testable and complete
- [x] The slice follows protocol-first DI and existing auth/email patterns
- [x] Risks and operational implications are called out clearly

## Review Feedback

**Reviewer:** @lead-developer
**Date:** 2026-03-30
**Verdict:** approved

### Required Changes

- None. The previous required changes were resolved in the revised ADR/story/PR slice and the
  re-review found no blocking issues.

### Suggestions (Optional)

- None.

### Decision Approvals

- [x] Use a dedicated `password_reset_tokens` seam
- [x] Keep generic success on request
- [x] Revoke all active sessions after reset
- [x] Restrict reset to local accounts
- [x] Require explicit login after reset

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | ADR-0078 | Drafted the local password-reset contract and security posture |
| 2 | EPIC-02 | Updated the identity epic scope and story list for password recovery |
| 3 | ST-02-07 / PR-0172 | Drafted the implementation slice and execution plan |
| 4 | ADR-0078 / ST-02-07 / PR-0172 | Added the one-active-token issuance invariant and invalidation of older pending tokens on new request |
| 5 | ADR-0078 / ST-02-07 / PR-0172 | Defined the public throttling contract: application-owned 60-second normalized-email cooldown plus edge/ingress IP abuse protection |
| 6 | ADR-0078 / ST-02-07 / PR-0172 | Locked down exact `forgot-password` and `reset-password` HTTP statuses, bodies, and reset error codes |
| 7 | ADR-0078 / ST-02-07 / PR-0172 | Strengthened verification to prove hashed token lookup, second-request invalidation, and multi-session revocation |
| 8 | ADR-0078 / ST-02-07 / PR-0172 | Made the reset-token-at-rest decision explicit: store `token_hash`, not plaintext tokens |
