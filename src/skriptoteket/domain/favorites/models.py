from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, model_validator


class FavoriteCatalogItemKind(StrEnum):
    TOOL = "tool"
    CURATED_APP = "curated_app"


class FavoriteCatalogRef(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: FavoriteCatalogItemKind
    tool_id: UUID | None = None
    app_id: str | None = None
    created_at: datetime

    @model_validator(mode="after")
    def _validate_kind(self) -> "FavoriteCatalogRef":
        if self.kind is FavoriteCatalogItemKind.TOOL and self.tool_id is None:
            raise ValueError("tool_id is required for tool favorites")
        if self.kind is FavoriteCatalogItemKind.CURATED_APP and not self.app_id:
            raise ValueError("app_id is required for curated app favorites")
        return self


class UserFavoriteTool(BaseModel):
    model_config = ConfigDict(frozen=True, from_attributes=True)

    user_id: UUID
    tool_id: UUID
    created_at: datetime


class UserFavoriteCuratedApp(BaseModel):
    model_config = ConfigDict(frozen=True, from_attributes=True)

    user_id: UUID
    app_id: str
    created_at: datetime
