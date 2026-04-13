---
type: review
id: REV-PR-0261
title: "Review: PR-0261 login register reset affordance and redirect contract"
status: approved
owners: "agents"
created: 2026-04-13
updated: 2026-04-13
reviewer: "lead-developer"
prs:
  - PR-0261
links:
  - EPIC-28
  - ST-28-12
  - HuleEdu TASK-0327
  - REV-TASK-0327-01
---

## TL;DR

Approved for implementation after the scope refinement that adds the
Skriptoteket no-side-effect consumer probe route required by HuleEdu
`TASK-0327` final live apply.

## Problem Statement

The provider can own lifecycle routes, but Skriptoteket still needs a humane,
clear entry point that does not reveal implementation details or send users
through unsafe continuation URLs.

## Proposed Solution

Keep HuleEdu as lifecycle authority and update Skriptoteket's visible auth
choices, generated URLs, callback handling, and failure copy around user tasks:
sign in, create account, reset password, continue.

This approval also covers the smallest hidden diagnostic route needed by
HuleEdu `TASK-0327`: a same-origin Skriptoteket API endpoint that verifies the
Gateway-signed `InternalIdentityContextV1`, validates the Skriptoteket product
context, returns only sanitized decoded claim proof, and performs no local
projection/provisioning side effects.

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/backlog/prs/pr-0261-st-28-12-login-register-reset-affordance-and-redirect-contract.md` | Scope and redirect contract | 10 min |
| `docs/backlog/stories/story-28-12-real-standalone-lifecycle-and-auth-entry-proof.md` | Parent story expectations | 5 min |
| HuleEdu `TASK-0327` | Provider lifecycle prerequisite | 5 min |

**Total estimated time:** ~20 minutes

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| HuleEdu remains lifecycle authority | Avoid restoring local auth ownership | [x] |
| Links land on direct action pages | Deliberate clicks should not make users pass through a generic HuleEdu stopover | [x] |
| Visible copy uses user tasks | Users do not need to understand realms or projections | [x] |
| All auth URLs keep safe continuation | Prevent hostile or looping return paths | [x] |
| Consumer probe is no-side-effect and sanitized | HuleEdu needs live signed-context proof without exposing raw token/header material or mutating local users | [x] |

## Review Checklist

- [x] Scope is bounded to UI/redirect/callback behavior
- [x] Login/register/forgot/verify/reset links land directly on the requested action page
- [x] User-facing copy avoids internals
- [x] `app` and product realm parameters are explicit
- [x] Safe `next` behavior is preserved
- [x] Consumer probe returns sanitized signed-context claim proof only
- [x] Consumer probe avoids projection/provisioning side effects
- [x] Live UI verification is required

## Review Feedback

**Reviewer:** lead-developer
**Date:** 2026-04-13
**Verdict:** changes_requested

### Scope Under Review

- `docs/backlog/prs/pr-0261-st-28-12-login-register-reset-affordance-and-redirect-contract.md`
- `docs/backlog/stories/story-28-12-real-standalone-lifecycle-and-auth-entry-proof.md`
- HuleEdu `TASK-0327` and retained review `REV-TASK-0327-01`

Public/user surfaces affected: the signed-out auth entry, lifecycle handoff links,
`next` sanitization, `/auth/callback` recovery copy, and browser-observed HuleEdu
direct-action landing behavior.

### Required Changes

1. **high: Provider direct-action contract is still under review.**

   `docs/backlog/prs/pr-0261-st-28-12-login-register-reset-affordance-and-redirect-contract.md:18`
   depends on HuleEdu `REV-TASK-0327-01`, but that provider review is currently
   `changes_requested`. The local UI can point at user-task actions, but approval requires the
   upstream lifecycle URL/action matrix to be accepted first.

   **Fix:** gate `PR-0261` on an approved `REV-TASK-0327-01`, then consume the accepted
   provider route matrix verbatim instead of relying on generic "action-specific page" wording.

   **Proof requirement:** after the provider review is approved, update this review with the
   accepted route matrix reference and run `pdm run docs-validate`.

2. **high: The PR does not freeze the exact link-target matrix Skriptoteket must build.**

   `docs/backlog/prs/pr-0261-st-28-12-login-register-reset-affordance-and-redirect-contract.md:54`
   says all actions should browser-navigate through action-specific HuleEdu routes. That does
   not tell implementers whether forgot-password and reset share `/auth/password-reset`, which
   fields are required on each action, or how token-bearing verification/reset links differ from
   product-originating links.

   **Fix:** add a concrete action matrix to `PR-0261` before implementation. It should cover
   login, register, password-reset request, password-reset completion, and email verification;
   list the HuleEdu path, required `app`, `product_identity_realm`, `return_to`, safe `next`,
   token handling, and the expected first interactive page for each action.

   **Proof requirement:** add or update frontend tests for the URL builder and lifecycle
   handoff views so each action emits the exact approved HuleEdu URL shape, drops hostile or
   looping `next`, and never targets local `/api/v1/auth/*` browser endpoints.

3. **medium: Verification needs named frontend and live-browser gates.**

   `docs/backlog/prs/pr-0261-st-28-12-login-register-reset-affordance-and-redirect-contract.md:68`
   requires affected tests and a live check, but not the exact command surfaces or expected
   browser evidence.

   **Fix:** name the focused Vitest files once implementation scope is known and include
   `pdm run fe-type-check`, `pdm run fe-lint`, `pdm run docs-validate`, and `git diff --check`.
   The live check must record, in `.agents/handoff.md`, the observed first interactive page for
   login, create-account, forgot-password, verification, and reset.

   **Proof requirement:** retain screenshots or sanitized Playwright artifacts for the live
   action-page checks, with no tokens or raw magic links.

### Suggestions (Optional)

None.

### Decision Approvals

- [x] HuleEdu-owned lifecycle
- [x] Direct-action links
- [x] User-task copy
- [x] Safe continuation

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | `PR-0261` | Initial review-ready auth-entry slice |
| 2 | `ST-28-12` / `PR-0261` | Marked the story and PR blocked until HuleEdu `REV-TASK-0327-01` approves the provider lifecycle route matrix |
| 3 | `PR-0261` | Added a concrete consumer action matrix for login, registration, password-reset request, password-reset completion, and email verification |
| 4 | `PR-0261` | Froze required `app`, `product_identity_realm`, `return_to`, safe `next`, token, and first-interactive-page rules for each action |
| 5 | `PR-0261` | Added exact focused Vitest command, `fe-type-check`, `fe-lint`, docs/diff gates, expected `pr-0261-auth-action-matrix` live proof command, and sanitized artifact directory |
| 6 | `PR-0261` / `ST-28-12` | Replaced the old "wait until HuleEdu TASK-0327 is done" block with the accepted provider-contract gate: `REV-TASK-0327-01` is approved, `TASK-0327` remains in progress until the Skriptoteket probe route exists and HuleEdu reruns final live apply |
| 7 | `PR-0261` | Added the hidden no-side-effect consumer probe route contract for sanitized decoded `InternalIdentityContextV1` claim proof through the HuleEdu Gateway proxy |
| 8 | `PR-0261` | Required direct external action anchors and auto-handoff compatibility lifecycle routes so local Skriptoteket pages are not the first interactive action page |

## Approval 2026-04-13

**Reviewer:** lead-developer
**Verdict:** approved

`REV-TASK-0327-01` is approved, so the HuleEdu provider implementation
contract is accepted. `PR-0261` may now start and must implement both the
original auth-entry/direct-action URL contract and the hidden no-side-effect
consumer probe route.

That downstream rerun is now complete. HuleEdu `TASK-0327` retained its final
`status=ok` artifact after calling the new Skriptoteket diagnostics route, so
`PR-0261` can hand off to `PR-0262` for Skriptoteket-side projection and local
role proof.

## Re-review Request 2026-04-13

Please re-review the amended `PR-0261` / `ST-28-12` contract. The local
consumer slice is now explicitly blocked until HuleEdu `REV-TASK-0327-01`
approves the provider direct-action route matrix, so the review should evaluate
whether the Skriptoteket-side contract is now precise enough to approve once
that upstream gate clears.

The requested local corrections have been applied:

- Provider approval is a hard implementation gate.
- The action matrix now names each HuleEdu path, required query fields, token
  rule, safe `next` handling, and expected first interactive page.
- Forgot-password request and reset completion both target
  `/auth/password-reset`; only reset completion forwards a token.
- Verification targets `/auth/email-verification` with a required redacted
  token.
- Canonical links may not target local `/api/v1/auth/*` browser endpoints or
  provider `/v1/auth/*` API endpoints.
- Verification now names focused frontend test files, frontend type/lint gates,
  `pdm run docs-validate`, `git diff --check`, the expected live proof command,
  and the sanitized artifact directory.

## Closeout Note 2026-04-13

HuleEdu reran `TASK-0327` live apply against
`/api/v1/diagnostics/huleedu-internal-identity` and retained a final
`status=ok` artifact. The HuleEdu runner now accepts the approved sanitized
diagnostics shape without requiring raw signed-context email or raw
`realm_subject_id` in retained signed-context proof. This closes the provider
runner blocker that `PR-0261` existed to unblock; `PR-0262` now consumes that
artifact as upstream proof.
