from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, JsonValue


class ToolSessionState(BaseModel):
    model_config = ConfigDict(frozen=True)

    tool_id: UUID
    context: str
    state: dict[str, JsonValue]
    state_rev: int


class GetToolSessionStateQuery(BaseModel):
    model_config = ConfigDict(frozen=True)

    tool_id: UUID
    context: str


class GetToolSessionStateResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    session_state: ToolSessionState


class UpdateToolSessionStateCommand(BaseModel):
    model_config = ConfigDict(frozen=True)

    tool_id: UUID
    context: str
    expected_state_rev: int
    state: dict[str, JsonValue]


class UpdateToolSessionStateResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    session_state: ToolSessionState


class ClearToolSessionStateCommand(BaseModel):
    model_config = ConfigDict(frozen=True)

    tool_id: UUID
    context: str


class ClearToolSessionStateResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    session_state: ToolSessionState
