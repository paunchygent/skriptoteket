from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue


class NoChangeStateUpdate(BaseModel):
    """State was omitted/null: preserve existing session state."""

    model_config = ConfigDict(frozen=True)

    kind: Literal["no_change"] = "no_change"


class ClearStateUpdate(BaseModel):
    """State was explicitly set to {}: clear existing session state."""

    model_config = ConfigDict(frozen=True)

    kind: Literal["clear"] = "clear"


class SetStateUpdate(BaseModel):
    """State was explicitly provided: overwrite existing session state."""

    model_config = ConfigDict(frozen=True)

    kind: Literal["set"] = "set"
    state: dict[str, JsonValue]


StateUpdate = Annotated[
    NoChangeStateUpdate | ClearStateUpdate | SetStateUpdate,
    Field(discriminator="kind"),
]


def resolve_state_update(
    *,
    update: StateUpdate,
    current_state: dict[str, JsonValue],
) -> dict[str, JsonValue]:
    if isinstance(update, NoChangeStateUpdate):
        return current_state
    if isinstance(update, ClearStateUpdate):
        return {}
    return update.state
