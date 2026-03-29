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
  - "Given a reset request for an active, verified local account, when the request is accepted, then the system creates a short-lived reset token and sends a password-reset email."
  - "Given a reset request for an unknown email, inactive account, unverified account, or non-local auth provider, when the request is submitted, then the API still returns the same generic success response without revealing account state."
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
  - Response: generic success message only
- `POST /api/v1/auth/reset-password`
  - Request: `{ token, new_password }`
  - Response: generic success message or domain error

Recommended error codes for reset execution:

- `INVALID_PASSWORD_RESET_TOKEN`
- `PASSWORD_RESET_TOKEN_EXPIRED`
- `VALIDATION_ERROR`

### Domain and application

- Add `PasswordResetToken` domain model and repository protocol.
- Add request/reset handlers in the identity application layer.
- Keep reset-token storage separate from email-verification tokens in the first slice.
- Reuse the existing password-strength validator.
- On successful reset:
  - update the password hash
  - clear lockout state
  - revoke all active sessions for the user
  - mark the used token and invalidate any remaining pending tokens for that user

### Email and configuration

- Add `reset_password.html` alongside the existing verification template.
- Add reset-specific settings for TTL and public base URL.
- Keep generic success semantics on request to avoid account enumeration.
- Add lightweight resend/request throttling per user based on latest token age.

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

- Unit tests for request/reset handlers, token validation, lockout reset, and session revocation.
- Route tests for anonymous request/reset endpoints.
- Frontend tests for forgot/reset routes and token-state UX.
- Manual proof:
  - request reset
  - receive reset link
  - reset password
  - confirm old password fails and new password works
  - confirm prior session is no longer usable
