---
type: review
id: REV-EPIC-02
title: "Review: Local password reset via emailed token"
status: pending
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
| Use a dedicated `password_reset_tokens` table instead of a generic shared email-action token table | Keeps semantics explicit and lowers implementation risk for the first recovery slice | [ ] |
| Return generic success from `forgot-password` for unknown, inactive, unverified, and federated accounts | Prevents account-state disclosure at the public request endpoint | [ ] |
| Revoke all active sessions and clear lockout state after successful reset | Makes reset a clear recovery/security boundary instead of just a hash swap | [ ] |
| Restrict the flow to `AuthProvider.LOCAL` accounts | Preserves the future HuleEdu identity boundary and avoids a hidden dual-auth fallback | [ ] |
| Require explicit login after reset instead of auto-login | Keeps the recovery flow simple and avoids adding a new anonymous-to-session elevation path | [ ] |

## Review Checklist

- [ ] ADR-0078 defines a clear reset-token contract and local-only boundary
- [ ] EPIC-02 scope stays appropriately narrow for identity recovery
- [ ] ST-02-07 acceptance criteria are testable and complete
- [ ] The slice follows protocol-first DI and existing auth/email patterns
- [ ] Risks and operational implications are called out clearly

## Review Feedback

**Reviewer:** @lead-developer
**Date:** 2026-03-30
**Verdict:** pending

### Required Changes

- Pending review.

### Suggestions (Optional)

- None yet.

### Decision Approvals

- [ ] Use a dedicated `password_reset_tokens` seam
- [ ] Keep generic success on request
- [ ] Revoke all active sessions after reset
- [ ] Restrict reset to local accounts
- [ ] Require explicit login after reset

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | ADR-0078 | Drafted the local password-reset contract and security posture |
| 2 | EPIC-02 | Updated the identity epic scope and story list for password recovery |
| 3 | ST-02-07 / PR-0172 | Drafted the implementation slice and execution plan |
