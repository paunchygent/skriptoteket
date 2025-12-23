---
type: story
id: ST-02-05
title: "Brute-force lockout"
status: ready
owners: "agents"
created: 2025-12-23
epic: "EPIC-02"
acceptance_criteria:
  - "Given a user with 5 failed login attempts, when they try to login again, then they see error 'Kontot är låst. Försök igen om 15 minuter.'"
  - "Given a locked user, when 15 minutes have passed, then they can attempt login again"
  - "Given a user with failed attempts, when they login successfully, then failed_login_attempts is reset to 0"
  - "Given a failed login attempt, then last_failed_login_at is updated"
  - "Given a successful login, then last_login_at is updated"
dependencies: ["ADR-0034"]
ui_impact: "Login error message shows lockout info"
data_impact: "Updates security fields on users table"
---

## Context

Without brute-force protection, attackers can attempt unlimited password guesses. This story adds account lockout after repeated failed attempts.

## Implementation notes

### Domain

New file `src/skriptoteket/domain/identity/lockout.py`:

```python
LOCKOUT_THRESHOLD = 5
LOCKOUT_DURATION_MINUTES = 15

def is_locked_out(user: User) -> bool:
    if user.locked_until is None:
        return False
    return datetime.now(UTC) < user.locked_until

def record_failed_attempt(user: User) -> User:
    attempts = user.failed_login_attempts + 1
    locked_until = None
    if attempts >= LOCKOUT_THRESHOLD:
        locked_until = datetime.now(UTC) + timedelta(minutes=LOCKOUT_DURATION_MINUTES)
    return user.model_copy(update={
        "failed_login_attempts": attempts,
        "locked_until": locked_until,
        "last_failed_login_at": datetime.now(UTC),
    })

def reset_failed_attempts(user: User) -> User:
    return user.model_copy(update={
        "failed_login_attempts": 0,
        "locked_until": None,
        "last_login_at": datetime.now(UTC),
    })
```

### Login handler changes

Update `src/skriptoteket/application/identity/handlers/login.py`:

1. Load user by email (even before password check)
2. Check `is_locked_out(user)` → raise `ACCOUNT_LOCKED` error
3. On password mismatch: `record_failed_attempt(user)`, persist, raise `INVALID_CREDENTIALS`
4. On success: `reset_failed_attempts(user)`, persist, continue with session creation

### Repository changes

Add to `UserRepository`:

```python
async def update_security_fields(
    user_id: UUID,
    failed_login_attempts: int,
    locked_until: datetime | None,
    last_login_at: datetime | None,
    last_failed_login_at: datetime | None,
) -> None
```

### Error codes

- `ACCOUNT_LOCKED` (423) - User is locked out
- Include `retry_after_seconds` in error detail for client display

### SPA

Update login error handling to show lockout message with countdown if `ACCOUNT_LOCKED` error.
