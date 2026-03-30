---
type: pr
id: PR-0174
title: "Recovery email hardening and verification resend discoverability"
status: in_progress
owners: "agents"
created: 2026-03-30
updated: 2026-03-30
stories:
  - "ST-02-10"
tags: ["identity", "email", "frontend", "production-bugfix"]
acceptance_criteria:
  - "Verified local users can request a password-reset email without the reset template failing before send."
  - "The verification email no longer references a remote image asset that renders as broken in common mail clients."
  - "Unverified local users can discover the existing resend-verification path from the auth recovery UX without needing the original verification link."
  - "The slice preserves the existing resend-verification generic-success and cooldown semantics."
---

## Problem

The production auth recovery surface currently has a split failure mode:

1. password-reset requests for eligible verified users can mint a reset token but still fail before
   outbound send because `reset_password.html` does not satisfy the template renderer contract, and
2. users who never completed email verification do not get a clear recovery path from the places
   they naturally end up (`Glömt lösenord`, login failure), even though backend resend support
   already exists.

On top of that, the current verification email includes a remote header image that appears broken in
mail clients that block or mishandle the asset.

## Goal

Ship one focused auth/email polish slice that:

1. makes password-reset email rendering reliable,
2. removes the broken verification-email image dependency, and
3. exposes the resend-verification path where users actually look for help.

## Non-goals

- New identity-provider behavior or federated-account recovery.
- A new verification-token persistence model.
- Changing the anonymous security posture of `resend-verification`.
- A broad redesign of all auth views.

## Implementation plan

### 1. Docs and traceability

- Add `ST-02-10` under `EPIC-02`.
- Record the production root cause in the story/PR context so future sessions know this was not an
  SMTP outage.

### 2. Email template hardening

- Add the required HTML subject comment to `reset_password.html`.
- Remove the header image from `verify_email.html` and keep the rest of the template intact.

### 3. Auth recovery UX

- Update `ForgotPasswordView.vue` to expose a resend-verification path alongside the reset request
  guidance.
- Update `LoginModal.vue` so an `EMAIL_NOT_VERIFIED` failure offers a direct resend-verification
  action using the typed email address.
- Keep success handling aligned with the existing anonymous/generic backend contract.

### 4. Stale copy cleanup

- Update any auth help copy that still says password reset is unavailable.

## Test plan

### Frontend

- `ForgotPasswordView.spec.ts` covers the resend-verification affordance and generic success state.
- `LoginModal.spec.ts` covers the `EMAIL_NOT_VERIFIED` recovery affordance.

### Backend / template

- If template-only changes are sufficient, keep backend verification at the route/integration level
  by proving a real reset request no longer logs the renderer error.

### Manual proof

- Run local backend + SPA.
- Verify a password-reset request for a verified local account no longer logs `Template
  reset_password.html missing subject comment`.
- Verify the verification email no longer references the removed header image.
- Verify the resend-verification affordance from both forgot-password and login modal flows.

## Rollback plan

- Revert the auth view changes if the UX needs to be reconsidered.
- Revert the template edits if an unexpected mail-client regression appears.
- The existing backend resend-verification and password-reset logic remain unchanged, so rollback is
  limited to presentation/template content for this slice.

## Review follow-up

- Ruthless review remediation is tracked in
  `docs/backlog/prs/pr-0176-review-remediation-for-recovery-email-hardening-and-resend-verification-ux.md`.
