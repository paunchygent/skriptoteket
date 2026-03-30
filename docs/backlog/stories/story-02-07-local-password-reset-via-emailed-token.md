---
type: story
id: ST-02-07
title: "Local password reset via emailed token"
status: ready
owners: "agents"
created: 2026-03-30
updated: 2026-03-30
epic: "EPIC-02"
acceptance_criteria:
  - "Given a visitor on the landing page or login modal, when they choose 'Glömt lösenord?', then they can request a password-reset email without being logged in."
  - "Given a reset request for an active, verified local account, when the request is accepted, then the system invalidates any older pending reset token for that user, creates exactly one new short-lived active reset token, and sends a password-reset email."
  - "Given a reset request for an unknown email, inactive account, unverified account, or non-local auth provider, when the request is submitted, then the API still returns the same generic `202 Accepted` success response without revealing account state."
  - "Given repeated `forgot-password` submissions for the same normalized email inside the cooldown window, when the request is submitted, then the application still returns the same generic `202 Accepted` response and does not issue a new active reset token."
  - "Given a user opens a valid reset link, when they submit a strong new password, then the password hash is replaced, lockout counters are cleared, and all active sessions for that user are revoked."
  - "Given a user submits an invalid, expired, or already-used reset token, when the reset is attempted, then the password is not changed and the UI shows a clear recovery error state."
  - "Given a password was reset successfully, when the user tries the old password, then login fails; when they try the new password, then login succeeds."
  - "Given the slice ships, when operators review the identity docs, then the reset flow and its session-revocation behavior are documented instead of relying on manual database hash replacement."
dependencies: ["ADR-0078", "ST-02-04", "ST-02-05", "ST-08-03"]
ui_impact: "New unauthenticated forgot-password and reset-password routes; login modal gets a 'Glömt lösenord?' entry point."
data_impact: "New password_reset_tokens table plus revoke-all-sessions-on-reset behavior for local accounts."
---

## Context

Skriptoteket already supports:

- local password login
- email verification
- authenticated password change
- brute-force lockout

The remaining gap is account recovery for users who have forgotten their password. Today that still
falls back to operator/database intervention, which is not acceptable for a teacher-facing
self-service product.

This slice should stay narrow: it adds local password recovery using the existing email/token stack
and keeps HuleEdu/federated identity out of scope.

## Implementation notes

### API

- `POST /api/v1/auth/forgot-password`
  - Request: `{ email }`
  - Response: `202 Accepted` + `{ "message": "Om kontot kan återställas skickas en återställningslänk." }`
- `POST /api/v1/auth/reset-password`
  - Request: `{ token, new_password }`
  - Success: `200 OK` + `{ "message": "Lösenordet har återställts. Logga in med ditt nya lösenord." }`

Required error codes and statuses for reset execution:

- `400` + `INVALID_PASSWORD_RESET_TOKEN`
- `400` + `PASSWORD_RESET_TOKEN_EXPIRED`
- `400` + `VALIDATION_ERROR`

### Domain and application

- Add `PasswordResetToken` domain model and repository protocol.
- Add request/reset handlers in the identity application layer.
- Keep reset-token storage separate from email-verification tokens in the first slice.
- Store reset tokens hashed at rest; presented tokens are hashed before lookup.
- Reuse the existing password-strength validator.
- On request:
  - invalidate any older pending reset tokens for the user before creating a new one
  - guarantee that only one active reset token exists per user at a time
- On successful reset:
  - update the password hash
  - clear lockout state
  - revoke all active sessions for the user
  - mark the used token and invalidate any remaining pending tokens for that user

### Email and configuration

- Add `reset_password.html` alongside the existing verification template.
- Add reset-specific settings for TTL and public base URL.
- Keep generic success semantics on request to avoid account enumeration.
- Define request throttling as part of the contract:
  - application-owned `60` second cooldown keyed by normalized email for every `forgot-password`
    request, even when the account is unknown or ineligible
  - ingress/edge IP throttling documented as an operational hardening layer outside the
    application-owned behavior contract

### SPA

- Add `/forgot-password` and `/reset-password` landing-page routes.
- Add a "Glömt lösenord?" action to `LoginModal.vue`.
- Use the existing email-verification page as the visual/interaction baseline for:
  - loading
  - success
  - expired token
  - invalid token

### Documentation and operator readiness

- Update the relevant identity/auth docs and the user-management runbook so they describe the new
  recovery path and session-revocation behavior.
- Do not leave the direct DB hash update path as the primary operational guidance for routine local
  account recovery once this story ships.

### Verification

- Unit tests for request/reset handlers, token validation, hashed token lookup, issuance invalidation,
  cooldown behavior, lockout reset, and session revocation.
- Route tests for anonymous request/reset endpoints.
- Frontend tests for forgot/reset routes and token-state UX.
- Manual proof:
  - request reset
  - receive reset link
  - request a second reset and confirm the first token is no longer usable
  - reset password
  - confirm old password fails and new password works
  - confirm at least two pre-existing sessions or cookie jars are both invalid after reset
