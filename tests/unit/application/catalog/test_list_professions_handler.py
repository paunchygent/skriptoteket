from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from skriptoteket.application.catalog.handlers.list_professions import ListProfessionsHandler
from skriptoteket.application.catalog.queries import ListProfessionsQuery
from skriptoteket.protocols.catalog import ProfessionRepositoryProtocol
from tests.fixtures.catalog_fixtures import make_profession


@pytest.mark.asyncio
async def test_list_professions_returns_repo_result(now: datetime) -> None:
    professions_list = [
        make_profession(slug="larare", label="Lärare", sort_order=10, now=now),
        make_profession(slug="rektor", label="Rektor", sort_order=40, now=now),
    ]

    professions = AsyncMock(spec=ProfessionRepositoryProtocol)
    professions.list_all.return_value = professions_list

    handler = ListProfessionsHandler(professions=professions)
    result = await handler.handle(ListProfessionsQuery())

    assert result.professions == professions_list
    professions.list_all.assert_awaited_once()
