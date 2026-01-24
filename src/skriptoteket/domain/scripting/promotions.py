from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class PromotionRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    request_id: str
    kind: Literal["session"]
    source_path: str
    name: str
    ref: str | None = None


class PromotionResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    request_id: str
    status: Literal["applied", "rejected"]
    ref: str | None = None
    reason: str | None = None


class PromotionEnvelope(BaseModel):
    model_config = ConfigDict(frozen=True)

    requests: list[PromotionRequest] = Field(default_factory=list)
    results: list[PromotionResult] = Field(default_factory=list)
