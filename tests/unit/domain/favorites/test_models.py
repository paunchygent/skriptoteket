from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from skriptoteket.domain.favorites.models import UserFavoriteCuratedApp, UserFavoriteTool


def test_user_favorite_tool_is_frozen() -> None:
    now = datetime.now(timezone.utc)
    favorite = UserFavoriteTool(user_id=uuid4(), tool_id=uuid4(), created_at=now)

    assert UserFavoriteTool.model_config.get("frozen") is True
    with pytest.raises(ValidationError):
        setattr(favorite, "user_id", uuid4())


def test_user_favorite_curated_app_is_frozen() -> None:
    now = datetime.now(timezone.utc)
    favorite = UserFavoriteCuratedApp(user_id=uuid4(), app_id="demo.counter", created_at=now)

    assert UserFavoriteCuratedApp.model_config.get("frozen") is True
    with pytest.raises(ValidationError):
        setattr(favorite, "app_id", "demo.timer")
