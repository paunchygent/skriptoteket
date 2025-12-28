from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AddFavoriteCommand(BaseModel):
    model_config = ConfigDict(frozen=True)

    catalog_item_id: UUID


class RemoveFavoriteCommand(BaseModel):
    model_config = ConfigDict(frozen=True)

    catalog_item_id: UUID


class FavoriteStatusResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: UUID
    is_favorite: bool
