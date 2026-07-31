---
type: adr
id: ADR-SKRIPT-0078
title: Local password reset via emailed token
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: accepted
deciders:
- user-lead
retired_ids:
- ADR-0078
---

## Context

### Context

Skriptoteket now supports local password authentication, server-side sessions, self-registration,
email verification, and authenticated password change. It does not yet support self-service
account recovery for users who have forgotten their password.

That leaves a teacher-facing gap and an operational gap:

- users with forgotten passwords currently need manual intervention
- the existing runbook still falls back to direct hash replacement in the database
- the current auth/email stack already includes token generation, SMTP delivery, HTML email
  templates, login lockout tracking, and session revocation primitives that should be reused
  instead of bypassed

We need a recovery flow that fits the existing local-account architecture, does not leak account
existence, and does not blur the future federation boundary where HuleEdu may own identity.

### Decision

### 1. Add a dedicated password-reset token model

Introduce a separate password-reset token aggregate and persistence table instead of reusing
`email_verification_tokens`.

The token record should include:

- `id`
- `user_id`
- `token_hash`
- `expires_at`
- `used_at`
- `created_at`

This remains intentionally parallel to email verification, but with its own semantics and lifecycle.
The first slice optimizes for clarity and low-risk implementation over premature generalization into
one generic "email action token" table.

Reset tokens are higher sensitivity than email-verification links, so the reset token itself must
not be stored in plaintext. The presented token is hashed before lookup.

At most **one active reset token** may exist per user at a time. When a new reset is issued, any
older pending reset tokens for that user are invalidated before the new token becomes active.

### 2. Add two local-auth recovery endpoints

Add anonymous SPA-facing endpoints:

- `POST /api/v1/auth/forgot-password`
- `POST /api/v1/auth/reset-password`

Behavior:

- `forgot-password` always returns a generic success message
- a reset email is sent only for active, verified, `AuthProvider.LOCAL` users
- unknown emails, inactive users, unverified users, and federated users still receive the same
  generic response
- `forgot-password` returns `202 Accepted` with a stable JSON body:
  `{ "message": "Om kontot kan återställas skickas en återställningslänk." }`
- `reset-password` accepts `token` plus `new_password`
- `reset-password` returns `200 OK` with a stable JSON body on success:
  `{ "message": "Lösenordet har återställts. Logga in med ditt nya lösenord." }`
- `reset-password` failure contract is explicit:
  - invalid token -> `400` + `INVALID_PASSWORD_RESET_TOKEN`
  - expired token -> `400` + `PASSWORD_RESET_TOKEN_EXPIRED`
  - weak password / malformed body -> `400` + `VALIDATION_ERROR`

No browser session or CSRF requirement is added to the anonymous request flow. These endpoints are
public by design and rely instead on generic responses, token entropy, expiry, and request-rate
limits.

Anonymous request throttling is a defined part of the contract:

- the **application layer** must enforce a normalized-email cooldown for `forgot-password`
  submissions, regardless of whether the email belongs to a local, federated, unknown, active, or
  inactive account
- the first slice should use a `60` second cooldown keyed by normalized email and still return the
  same generic `202` response when throttled
- the **edge/ingress layer** remains the owner of coarse IP-based abuse protection outside the
  application contract; this slice must document that operational expectation in the runbook, but
  the repo-owned implementation contract is the normalized-email cooldown

### 3. Successful reset changes password and revokes access

On successful password reset:

- validate the token is valid, unused, and unexpired
- validate password strength with the same policy as registration/profile change
- write the new Argon2 password hash
- clear `failed_login_attempts`, `locked_until`, and related lockout state
- revoke all active sessions for the user
- mark the reset token as used
- invalidate any other pending reset tokens for the same user

The flow does **not** auto-login the user after reset. They must explicitly log in again with the
new password.

The session-revocation contract is bulk revocation, not single-session best effort. After a
successful reset, every active session for the user must become unusable.

### 4. Keep the scope local-account only

Password reset applies only to local-password accounts.

Federated/HuleEdu identities remain outside scope:

- the generic request response must not reveal whether the account is local or federated
- the system must not invent a Skriptoteket-local fallback reset path for federated identities

### 5. Reuse the existing email stack and add a dedicated reset template

Reuse the existing:

- token generator
- SMTP/mock email sender
- Jinja2 email renderer
- SPA route pattern used by email verification

Add a dedicated email template and configuration for reset links, including a shorter reset TTL than
email verification. The recommended first reset TTL is **2 hours**.

### Consequences

- Users can recover local accounts without operator intervention.
- Successful reset becomes a stronger security boundary than the current authenticated
  password-change flow because all active sessions are revoked.
- The system gains another email-token table, which duplicates some mechanics but keeps the domain
  intent explicit and avoids cross-purpose token confusion.
- The existing auth documentation must be updated so the repo no longer describes manual DB hash
  replacement as the normal recovery path for local users.

## Decision

The retained source material above records the accepted decision and its consequences.

## Non-Decisions

This record does not authorize implementation beyond the retained decision.

## Consequences

The retained source material above records the accepted decision and its consequences.
