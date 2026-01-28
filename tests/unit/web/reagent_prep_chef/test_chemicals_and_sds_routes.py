from __future__ import annotations

from datetime import datetime

import httpx
import pytest

from skriptoteket.application.curated_apps.reagent_prep_chef import (
    ReagentPrepChefChemicalOption,
    ReagentPrepChefChemicalsResult,
)
from skriptoteket.config import Settings
from skriptoteket.domain.identity.models import Role
from skriptoteket.web.api.v1 import apps_reagent_prep_chef as reagent_prep_chef_api
from tests.fixtures.identity_fixtures import make_session, make_user
from tests.unit.web.reagent_prep_chef.test_support import (
    StubActorHandler,
    StubCurrentUserProvider,
    StubSdsStore,
    StubSessionRepository,
)


@pytest.mark.asyncio
async def test_list_chemicals_requires_auth(client: httpx.AsyncClient) -> None:
    response = await client.get(f"/api/v1/apps/{reagent_prep_chef_api.APP_ID}/chemicals")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_chemicals_returns_items(
    client: httpx.AsyncClient,
    settings: Settings,
    current_user_provider: StubCurrentUserProvider,
    sessions: StubSessionRepository,
    chemicals_handler: StubActorHandler[ReagentPrepChefChemicalsResult],
    now: datetime,
) -> None:
    user = make_user(role=Role.USER)
    session = make_session(user_id=user.id, now=now)

    current_user_provider.user = user
    sessions.sessions[session.id] = session
    chemicals_handler.set_result(
        ReagentPrepChefChemicalsResult(
            chemicals=[
                ReagentPrepChefChemicalOption(
                    key="NaCl", display_name="Natriumklorid", aliases=["Koksalt"]
                )
            ]
        )
    )

    client.cookies.set(settings.SESSION_COOKIE_NAME, str(session.id))
    response = await client.get(f"/api/v1/apps/{reagent_prep_chef_api.APP_ID}/chemicals")

    assert response.status_code == 200
    assert response.json()["chemicals"][0]["key"] == "NaCl"
    assert chemicals_handler.calls == [user]


@pytest.mark.asyncio
async def test_get_sds_returns_pdf(
    client: httpx.AsyncClient,
    settings: Settings,
    current_user_provider: StubCurrentUserProvider,
    sessions: StubSessionRepository,
    sds_store: StubSdsStore,
    now: datetime,
) -> None:
    user = make_user(role=Role.USER)
    session = make_session(user_id=user.id, now=now)

    current_user_provider.user = user
    sessions.sessions[session.id] = session
    sds_store.add(
        sds_ref="NaCl",
        filename="NaCl.pdf",
        content=b"%PDF-1.4 stub",
        media_type="application/pdf",
    )

    client.cookies.set(settings.SESSION_COOKIE_NAME, str(session.id))
    response = await client.get(f"/api/v1/apps/{reagent_prep_chef_api.APP_ID}/sds/NaCl")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/pdf")
    assert "NaCl.pdf" in response.headers["content-disposition"]
    assert response.content == b"%PDF-1.4 stub"
    assert sds_store.calls == ["NaCl"]


@pytest.mark.asyncio
async def test_get_sds_returns_404_for_missing(
    client: httpx.AsyncClient,
    settings: Settings,
    current_user_provider: StubCurrentUserProvider,
    sessions: StubSessionRepository,
    sds_store: StubSdsStore,
    now: datetime,
) -> None:
    user = make_user(role=Role.USER)
    session = make_session(user_id=user.id, now=now)

    current_user_provider.user = user
    sessions.sessions[session.id] = session

    client.cookies.set(settings.SESSION_COOKIE_NAME, str(session.id))
    response = await client.get(f"/api/v1/apps/{reagent_prep_chef_api.APP_ID}/sds/Unknown")

    assert response.status_code == 404
