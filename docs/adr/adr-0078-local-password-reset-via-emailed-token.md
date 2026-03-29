---
type: adr
id: ADR-0078
title: "Local password reset via emailed token"
status: proposed
owners: "agents"
deciders: ["user-lead"]
created: 2026-03-30
---

## Context

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

## Decision

### 1. Add a dedicated password-reset token model

Introduce a separate password-reset token aggregate and persistence table instead of reusing
`email_verification_tokens`.

The token record should include:

- `id`
- `user_id`
- `token`
- `expires_at`
- `used_at`
- `created_at`

This remains intentionally parallel to email verification, but with its own semantics and lifecycle.
The first slice optimizes for clarity and low-risk implementation over premature generalization into
one generic "email action token" table.

### 2. Add two local-auth recovery endpoints

Add anonymous SPA-facing endpoints:

- `POST /api/v1/auth/forgot-password`
- `POST /api/v1/auth/reset-password`

Behavior:

- `forgot-password` always returns a generic success message
- a reset email is sent only for active, verified, `AuthProvider.LOCAL` users
- unknown emails, inactive users, unverified users, and federated users still receive the same
  generic response
- `reset-password` accepts `token` plus `new_password`

No browser session or CSRF requirement is added to the anonymous request flow. These endpoints are
public by design and rely instead on generic responses, token entropy, expiry, and request-rate
limits.

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

## Consequences

- Users can recover local accounts without operator intervention.
- Successful reset becomes a stronger security boundary than the current authenticated
  password-change flow because all active sessions are revoked.
- The system gains another email-token table, which duplicates some mechanics but keeps the domain
  intent explicit and avoids cross-purpose token confusion.
- The existing auth documentation must be updated so the repo no longer describes manual DB hash
  replacement as the normal recovery path for local users.
