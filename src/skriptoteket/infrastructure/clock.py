from __future__ import annotations

from datetime import datetime, timezone

from skriptoteket.protocols.clock import ClockProtocol


class UTCClock(ClockProtocol):
    def now(self) -> datetime:
        return datetime.now(timezone.utc)
