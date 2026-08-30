"""Deterministic clock and UUID fixtures shared by application tests."""

from datetime import datetime
from uuid import UUID


class FixedClock:
    def __init__(self, now: datetime) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now


class FixedIdGenerator:
    def __init__(self, value: UUID) -> None:
        self._value = value

    def new_uuid(self) -> UUID:
        return self._value
