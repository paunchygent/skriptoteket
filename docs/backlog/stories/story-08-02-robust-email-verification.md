---
type: story
id: ST-08-02
title: "Robust email verification flow"
status: ready
owners: "agents"
created: 2025-12-30
epic: "EPIC-08"
acceptance_criteria:
  - "Registration rolls back if email send fails after retries"
  - "3 retry attempts with exponential backoff for transient SMTP errors"
  - "Clear error message returned to frontend on email failure"
  - "SMTP health check on application startup logs warning if unreachable"
  - "Unit tests cover all failure scenarios (transient, permanent, retry exhaustion)"
---

## Problem

Current registration flow has a critical flaw: user registration commits to database before email sending is confirmed. If SMTP fails, user is registered but never receives verification email, with no clear recovery path.

## Current Behavior

1. User submits registration
2. Transaction commits (user created, token created)
3. Email sending attempted **outside transaction**
4. If email fails: user exists but has no way to verify (except manual resend)
5. Registration returns 201 even when email failed

## Required Changes

### 1. Transactional Email Sending

- Email send must succeed before registration commits
- If email fails, rollback entire registration
- Return clear error to user: "Registration failed - please try again"

### 2. Retry Mechanism

- Implement retry with exponential backoff (3 attempts)
- Only fail registration after all retries exhausted

### 3. Error Handling Best Practices

- Distinguish between transient errors (network, timeout) and permanent errors (auth failed, invalid recipient)
- Transient: retry
- Permanent: fail fast with clear error message

### 4. SMTP Health Check

- Add SMTP connectivity check on startup (log warning if unreachable)
- Consider adding to `/healthz` endpoint as optional check

### 5. User Feedback

- If registration fails due to email, show actionable error
- Consider: queue-based email with status polling (future)

## Technical Notes

```python
# Conceptual approach
async with self._uow:
    # Create user + token
    ...

    # Send email INSIDE transaction
    email_sent = await self._send_with_retry(...)
    if not email_sent:
        raise DomainError(
            code=ErrorCode.EMAIL_SEND_FAILED,
            message="Kunde inte skicka verifieringsmail. Forsok igen."
        )

    # Only commits if we reach here
```

## References

- Current implementation: `src/skriptoteket/application/identity/handlers/register_user.py`
- SMTP sender: `src/skriptoteket/infrastructure/email/smtp_sender.py`
