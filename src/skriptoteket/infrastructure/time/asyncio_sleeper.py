from __future__ import annotations

import asyncio

from skriptoteket.protocols.sleeper import SleeperProtocol


class AsyncioSleeper(SleeperProtocol):
    async def sleep(self, seconds: float) -> None:
        await asyncio.sleep(seconds)
