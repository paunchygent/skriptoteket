---
type: pr
id: PR-0172
title: "Local password reset via emailed token"
status: ready
owners: "agents"
created: 2026-03-30
updated: 2026-03-30
stories:
  - "ST-02-07"
tags: ["identity", "security", "email", "backend", "frontend"]
acceptance_criteria:
  - "Local users can request a password-reset email without revealing whether an account exists."
  - "Only one active password-reset token may exist per user at a time; requesting a new reset invalidates any older pending token."
  - "A valid reset token allows a strong new password to be set and revokes all of the user's active sessions."
  - "Reset is limited to local-password identities and does not create a Skriptoteket-local recovery path for future federated users."
  - "The SPA provides clear unauthenticated forgot/reset routes that mirror the existing verification UX quality."
  - "Identity/runbook docs are updated so routine recovery no longer depends on direct database hash replacement."
---

## Problem

Skriptoteket now supports self-registration, email verification, brute-force lockout, and
authenticated password change, but it still lacks a self-service recovery flow for forgotten local
passwords. That leaves users dependent on manual operator intervention and leaves the runbook
pointing at direct database hash replacement as the routine fallback.

## Goal

Ship a local-account password reset flow that:

1. uses emailed one-time reset links,
2. preserves the existing local auth architecture,
3. avoids account enumeration,
4. revokes active sessions after a successful reset, and
5. keeps the federated/HuleEdu boundary explicit.

## Non-goals

- Magic-link login
- Password reset for HuleEdu/federated identities
- Replacing the authenticated profile password-change flow
- Collapsing verification and reset tokens into one generic token system in this first slice
- Broad auth-store cleanup beyond what is strictly required for the reset routes

## Implementation plan

### 1. Docs and contracts

- Add ADR-0078 for the reset-token and session-revocation contract.
- Update `EPIC-02` scope/story list to include password recovery.
- Keep a pending review record for the slice before implementation starts.

### 2. Domain and persistence

- Add `PasswordResetToken` domain model.
- Add repository protocol plus SQLAlchemy model/repository.
- Add Alembic migration for `password_reset_tokens`.

Recommended first schema:

- `id`
- `user_id`
- `token_hash`
- `expires_at`
- `used_at`
- `created_at`

Reset tokens are stored hashed at rest. Issuing a new reset request for an eligible user must
invalidate any older pending tokens before the new token becomes active, so each user has at most
one active reset token at a time.

### 3. Application layer

- Add `RequestPasswordResetHandler`.
- Add `ResetPasswordHandler`.
- Reuse existing password hashing and password-strength validation.
- Reuse lockout reset semantics from successful login.
- Add a session-revocation seam for "revoke all sessions for user".

### 4. Web/API layer

- Add `POST /api/v1/auth/forgot-password`.
- Add `POST /api/v1/auth/reset-password`.
- Keep request responses generic across unknown, inactive, unverified, and federated accounts.
- Lock the public contract to:
  - `forgot-password` -> `202 Accepted` + `{ "message": "Om kontot kan återställas skickas en återställningslänk." }`
  - `reset-password` success -> `200 OK` + `{ "message": "Lösenordet har återställts. Logga in med ditt nya lösenord." }`
  - `reset-password` invalid token -> `400` + `INVALID_PASSWORD_RESET_TOKEN`
  - `reset-password` expired token -> `400` + `PASSWORD_RESET_TOKEN_EXPIRED`
  - `reset-password` weak password / malformed body -> `400` + `VALIDATION_ERROR`
- Define anonymous throttling as part of the slice:
  - application-owned `60` second cooldown keyed by normalized email, returning the same generic
    `202` response even when throttled
  - edge/ingress-owned coarse IP abuse throttling documented as an operational requirement

### 5. Email + config

- Add `reset_password.html`.
- Add settings for reset TTL and base URL.
- Reuse SMTP/mock email sender and existing template renderer.

### 6. SPA

- Add `/forgot-password` and `/reset-password`.
- Add the forgot-password entry point from the login modal.
- Follow the `VerifyEmailView` interaction model for loading/success/expired/invalid states.

### 7. Docs and runbook cleanup

- Update auth/identity docs that still describe the older admin-provisioned-only posture as the
  live reality.
- Update the user-management runbook so local password recovery documents the new flow and the
  revoke-active-sessions behavior.

## Test plan

### Unit tests

- Request handler creates tokens only for eligible local verified accounts.
- Request handler returns generic success for ineligible/unknown accounts.
- Requesting a second reset invalidates the first token and leaves exactly one active token.
- Request throttling returns the same generic `202` contract and does not mint a new active token
  during the cooldown window.
- Reset handler accepts valid token, updates hash, clears lockout, revokes sessions.
- Reset handler rejects invalid, expired, or used tokens.

### Integration tests

- Repository coverage for `password_reset_tokens`.
- Repository coverage for hashed token lookup and issuance invalidation semantics.
- Session-revocation coverage proves at least two active sessions for the same user are both
  invalidated after reset.
- Migration idempotency coverage for the new table.

### Route/API tests

- `forgot-password` success body/status is stable for eligible, unknown, and throttled requests.
- `reset-password` success/error bodies and statuses match the documented contract.

### Frontend tests

- Forgot-password route submits and shows neutral success.
- Reset-password route handles success, invalid token, and expired token states.
- Login modal exposes the forgot-password entry point.

### Manual proof

- Run local backend + SPA.
- Request a reset for a local verified account.
- Request a second reset and confirm the first token is no longer usable.
- Use the newest emailed reset link.
- Confirm old password fails, new password works, and prior session is invalidated.
- Confirm at least two pre-existing sessions or cookie jars are both invalid after reset.
- If ingress throttling is part of the environment, record the operational verification path in the
  runbook.

## Rollback plan

- Provide a downgrade path that drops `password_reset_tokens`.
- If the email/reset flow is unstable, disable the new routes and UI entry points while preserving
  the existing profile password-change flow.
- The previous manual operator recovery path remains an emergency fallback until the runbook is
  updated after the slice is proven locally.
