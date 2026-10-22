"""Protocol seam for HuleEdu's LLM provider door.

Purpose:
    The one client every paid AI call goes through (ST-SKRIPT-41-01 B1, C2):
    it owns the internal key, the user id, the exempt flag and the
    paid-overage mode, while providers keep their OpenAI request bodies and
    parse the relayed OpenAI answer.

Relationships:
    Implemented by ``infrastructure.llm.door.client.HuleEduLlmDoorClient``;
    consumed by the exam providers under ``infrastructure.llm.openai``.
    Deterministic replays substitute a fake at this seam (B6).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from pydantic import JsonValue

from skriptoteket.domain.llm_door import AiDoorCaller


class DoorOperation(StrEnum):
    """The door's two OpenAI routes."""

    RESPONSES = "responses"
    DECISIONS = "decisions"


@dataclass(frozen=True, slots=True)
class DoorReply:
    """One relayed door answer: OpenAI's, or a door refusal that is not a limit or capacity 429."""

    status_code: int
    headers: Mapping[str, str]
    body: bytes

    @property
    def is_success(self) -> bool:
        return 200 <= self.status_code < 300


class DoorTimeout(Exception):
    """The door call timed out."""


class DoorRequestFailed(Exception):
    """The door call failed before an answer was received."""


class LlmDoorClientProtocol(Protocol):
    """Send one OpenAI request body through the door for ``caller``."""

    async def send(
        self,
        *,
        operation: DoorOperation,
        payload: Mapping[str, JsonValue],
        caller: AiDoorCaller,
        timeout_seconds: float,
    ) -> DoorReply:
        """Return the relayed answer.

        Raises ``AiDailyLimitReached`` for a pool, user-share or USD-ceiling
        429, ``AiDoorBusy`` when no room is found for the call (a process or
        connection slot not free in time, or a door capacity 429 still
        refused after its Retry-After retries), ``DoorTimeout`` on timeout and
        ``DoorRequestFailed`` when no answer arrived. Every other answer
        returns as a ``DoorReply``; a capacity 429 never does.
        """
        ...
