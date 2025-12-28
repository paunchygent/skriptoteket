from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from skriptoteket.application.catalog.queries import ListAllToolsResult
from skriptoteket.protocols.catalog import ListAllToolsHandlerProtocol
from skriptoteket.web.api.v1 import catalog as catalog_api
from tests.fixtures.identity_fixtures import make_user


def _unwrap_dishka(fn):
    return getattr(fn, "__dishka_orig_func__", fn)


@pytest.mark.asyncio
async def test_list_all_tools_parses_query_params() -> None:
    handler = AsyncMock(spec=ListAllToolsHandlerProtocol)
    handler.handle.return_value = ListAllToolsResult(items=[], professions=[], categories=[])

    user = make_user()
    result = await _unwrap_dishka(catalog_api.list_all_tools)(
        handler=handler,
        user=user,
        professions="Larare, ,",
        categories="Svenska,Matematik",
        q="  Ordlista  ",
    )

    assert result.items == []
    query = handler.handle.call_args.kwargs["query"]
    assert query.profession_slugs == ["larare"]
    assert query.category_slugs == ["svenska", "matematik"]
    assert query.search_term == "Ordlista"
