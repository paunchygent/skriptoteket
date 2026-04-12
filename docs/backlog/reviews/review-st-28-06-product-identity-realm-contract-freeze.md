---
type: review
id: REV-ST-28-06
title: "Review: ST-28-06 product identity realm ADR and contract freeze"
status: approved
owners: "agents"
created: 2026-04-12
updated: 2026-04-12
reviewer: "Codex ruthless-code-review"
stories:
  - ST-28-06
adrs:
  - ADR-0083
links:
  - EPIC-28
  - ADR-0076
  - ADR-0082
  - PR-0253
  - PR-0254
  - PR-0255
  - REV-PR-0253
  - REF-hule-education-product-identity-realms-and-skriptoteket-standalone-identity
---

## TL;DR

`ST-28-06` is approved after tightening `ADR-0083` from a direction memo into a contract freeze.
The accepted contract keeps Hule Education as the browser session, CSRF, gateway, and ceremony
authority while preserving Skriptoteket standalone product identity, realm-aware projection, and
local RBAC. `PR-0254` was intentionally held until the login, standalone lifecycle, and projection
stories implemented this realm-aware contract; after `PR-0258`, that final proof lane is ready.

## Problem Statement

`PR-0253` correctly retired Skriptoteket-local browser auth authority, but the follow-up work could
still accidentally certify the wrong product outcome: a HuleEdu-school-only login path presented as
final Skriptoteket login. The repo needs a retained decision gate that distinguishes the umbrella
browser session from product identity realms, local projections, and local authorization before
cross-app proof resumes.

## Proposed Solution

Accept `ADR-0083` as the governing product identity realm contract after freezing:

- the core vocabulary for browser session, product identity realm, active app, realm subject,
  projection, and local RBAC
- the first accepted realms: `skriptoteket_standalone` and `huleedu_school`
- the browser ceremony rule that login anchors must target a browser-navigable
  Hule Education `app=skriptoteket` ceremony, not a POST-only auth API
- the realm-aware signed context fields required before final proof
- the projection key target `(product_identity_realm, realm_subject_id)`
- the fail-closed provisioning rule when signed claims are insufficient
- the rejected options that would collapse standalone identity or revive local browser auth

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/adr/adr-0083-hule-education-product-identity-realms-for-skriptoteket-login.md` | Governing decision and frozen contract | 20 min |
| `docs/backlog/stories/story-28-06-product-identity-realm-adr-and-contract-freeze.md` | Story scope and acceptance criteria | 8 min |
| `docs/reference/ref-hule-education-product-identity-realms-and-skriptoteket-standalone-identity.md` | Reference direction and research questions | 10 min |
| `docs/backlog/epics/epic-28-skriptoteket-auth-authority-cutover-to-huleedu.md` | Epic sequencing and dependency impact | 8 min |
| `docs/backlog/stories/story-28-07-hule-education-hosted-skriptoteket-login-ceremony.md` | Login ceremony consumer story | 5 min |
| `docs/backlog/stories/story-28-08-skriptoteket-standalone-registration-and-password-lifecycle.md` | Standalone lifecycle consumer story | 5 min |
| `docs/backlog/stories/story-28-09-realm-aware-projection-provisioning-and-local-rbac.md` | Realm-aware projection consumer story | 5 min |
| `docs/backlog/stories/story-28-04-cross-app-auth-cutover-smoke-and-operator-runbook-proof.md` | Final smoke dependency and proof scope | 5 min |
| `docs/backlog/prs/pr-0254-st-28-04-cross-app-auth-cutover-smoke-and-runbook-proof.md` | Final proof PR backlog wording | 5 min |

**Total estimated time:** ~71 minutes

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Accept `ADR-0083` as the contract freeze for product identity realms | Gives downstream login/projection work one retained source of truth | [x] |
| Keep Hule Education as browser session and ceremony authority | Preserves `ADR-0076` and avoids a hidden local auth bridge | [x] |
| Preserve `skriptoteket_standalone` as a distinct realm | Prevents a HuleEdu-school-only identity future from stranding standalone users | [x] |
| Require realm-aware signed context before final cross-app proof | Makes `PR-0254` prove the real target contract rather than a legacy provider shortcut | [x] |
| Keep projection and RBAC app-local | Preserves existing ownership, profile, AI preferences, and contributor/admin semantics | [x] |

## Review Checklist

- [x] Scope is bounded to decision review and contract freeze, not login implementation
- [x] `ADR-0083` distinguishes browser session, product identity realm, projection, and RBAC
- [x] Browser ceremony targets are browser-navigable and not POST-only auth API routes
- [x] Realm-aware signed context requirements are concrete enough for `ST-28-07` through `ST-28-09`
- [x] Projection cannot use realm-ambiguous `sub` alone as the final key
- [x] First-time provisioning fails closed unless signed claims are sufficient
- [x] `PR-0254` stayed blocked until the realm-aware implementation path existed
- [x] Rejected options prevent local browser auth bridges and provider-role RBAC drift

## Review Feedback

**Reviewer:** `Codex ruthless-code-review`
**Date:** `2026-04-12`
**Verdict:** `approved`

### Required Changes

None open. The initial review found that the proposed ADR was directionally correct but not
contract-freeze grade because it named realm concepts without freezing vocabulary, the ceremony
contract, projection key semantics, or provisioning fail-closed rules. Those gaps were resolved in
`ADR-0083` before approval.

### Findings

No open findings.

Resolved during review:

1. **high - signed context and projection key were too vague for downstream implementation**

   File reference:
   `docs/adr/adr-0083-hule-education-product-identity-realms-for-skriptoteket-login.md`

   The proposed ADR said the signed context should include an active realm and app, but it did not
   freeze the terms, allowed realms, realm subject, projection key, or provisioning requirements.
   That would have allowed `ST-28-07` through `ST-28-09` to implement incompatible interpretations
   while still claiming ADR compliance.

   Concrete resolution: `ADR-0083` now freezes accepted realms, the browser ceremony contract, the
   realm-aware signed-context contract, target projection key, provisioning claim floor, and rejected
   options.

   Proof requirement: downstream implementation must add focused tests around ceremony URL shape,
   realm-aware signed context, projection lookup/provisioning, and local RBAC. This review is
   docs-only; `pdm run docs-validate` is the required close-out gate.

### Suggestions (Optional)

- `ST-28-09` should decide whether the realm-aware context is an additive
  `InternalIdentityContextV1` extension or a versioned successor before changing code.
- The first implementation PR that adds `skriptoteket_standalone` projections should include an
  explicit migration/data policy for current `AuthProvider.LOCAL` users.

### Decision Approvals

- [x] Accept `ADR-0083` as the contract freeze for product identity realms
- [x] Keep Hule Education as browser session and ceremony authority
- [x] Preserve `skriptoteket_standalone` as a distinct realm
- [x] Require realm-aware signed context before final cross-app proof
- [x] Keep projection and RBAC app-local

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | `ADR-0083` | Accepted the ADR and added frozen terms, accepted realms, browser ceremony rules, signed context contract, projection/RBAC contract, and rejected options |
| 2 | `ST-28-06` | Moved the story to done and recorded the contract-freeze implementation summary |
| 3 | `EPIC-28` | Updated the implementation summary to show `ST-28-06` / `ADR-0083` are complete |
| 4 | `ST-28-07` | Moved the next login-ceremony story to ready after the ADR contract freeze unblocked it |
| 5 | `.agents/handoff.md` | Updated the current lane, status, verification, and next step |
