---
type: adr
id: ADR-0034
title: "Self-registration and HuleEdu-aligned user profiles"
status: proposed
owners: "agents"
deciders: ["user-lead"]
created: 2025-12-23
---

## Context

Skriptoteket currently uses admin-provisioned accounts only (ADR-0009). Users cannot self-register, and the identity model
lacks profile fields (name, display preferences) and security controls (brute-force protection).

To prepare for future HuleEdu integration (ADR-0011) and enable a standalone Skriptoteket deployment, we need:

1. **Self-registration** - Users create their own accounts
2. **User profiles** - Name fields and preferences matching HuleEdu's `UserProfile` model
3. **Password change** - Self-service password management
4. **Brute-force protection** - Account lockout after failed login attempts

## Decision

### 1. Extend the identity model (HuleEdu-aligned)

Add security fields to `users` table:

```python
class User:
    # Existing fields...
    email_verified: bool = False          # For future email verification flow
    failed_login_attempts: int = 0
    locked_until: datetime | None = None
    last_login_at: datetime | None = None
    last_failed_login_at: datetime | None = None
```

Create separate `user_profiles` table (matches HuleEdu structure):

```python
class UserProfile:
    user_id: UUID                         # FK to users.id
    first_name: str | None = None
    last_name: str | None = None
    display_name: str | None = None       # Optional override for UI
    locale: str = "sv-SE"                 # User preference
    created_at: datetime
    updated_at: datetime
```

### 2. Self-registration endpoint

Add `POST /api/v1/auth/register`:

- Input: `email`, `password`, `first_name`, `last_name`
- Creates `User` with `role=user` and `email_verified=false`
- Creates `UserProfile` atomically
- Auto-login on success (sets session cookie)
- **Note**: Email verification flow is deferred (users can login without verifying for now)

### 3. Profile API

Add `GET/PATCH /api/v1/profile`:

- View and update profile fields (name, display_name, locale)
- `POST /api/v1/profile/password` - Change password (requires current password)
- `PATCH /api/v1/profile/email` - Change email (sets `email_verified=false`)

### 4. Brute-force lockout

Lockout policy:

- **Threshold**: 5 failed login attempts
- **Duration**: 15 minutes
- **Reset**: On successful login

Login flow changes:

1. Check `locked_until` before authentication
2. On failure: increment `failed_login_attempts`, set lockout if threshold reached
3. On success: reset `failed_login_attempts`, update `last_login_at`

### 5. Keep admin provisioning

Existing `provision-user` CLI and handler remain unchanged. Admin-provisioned accounts get `email_verified=true` by default.

## Consequences

- Users can self-register and manage their own profiles
- Identity model aligns with HuleEdu for future federation
- Brute-force protection mitigates credential stuffing attacks
- Email verification infrastructure is ready but not enforced (can enable later)
- Existing admin-provisioned accounts continue to work unchanged
