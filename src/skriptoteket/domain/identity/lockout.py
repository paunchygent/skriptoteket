from __future__ import annotations

from datetime import datetime, timedelta

from skriptoteket.domain.identity.models import User

LOCKOUT_THRESHOLD = 5
LOCKOUT_DURATION = timedelta(minutes=15)


def is_locked_out(*, user: User, now: datetime) -> bool:
    if user.locked_until is None:
        return False
    return now < user.locked_until


def record_failed_attempt(*, user: User, now: datetime) -> User:
    attempts = user.failed_login_attempts + 1
    locked_until = None
    if attempts >= LOCKOUT_THRESHOLD:
        locked_until = now + LOCKOUT_DURATION

    return user.model_copy(
        update={
            "failed_login_attempts": attempts,
            "locked_until": locked_until,
            "last_failed_login_at": now,
            "updated_at": now,
        }
    )


def reset_failed_attempts(*, user: User, now: datetime) -> User:
    return user.model_copy(
        update={
            "failed_login_attempts": 0,
            "locked_until": None,
            "last_login_at": now,
            "updated_at": now,
        }
    )
