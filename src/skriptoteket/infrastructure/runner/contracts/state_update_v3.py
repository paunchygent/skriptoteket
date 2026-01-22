from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue


class StateUpdateNoChange(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: Literal["no_change"]


class StateUpdateClear(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: Literal["clear"]


class StateUpdateSet(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: Literal["set"]
    state: dict[str, JsonValue]


StateUpdate = Annotated[
    StateUpdateNoChange | StateUpdateClear | StateUpdateSet,
    Field(discriminator="kind"),
]
