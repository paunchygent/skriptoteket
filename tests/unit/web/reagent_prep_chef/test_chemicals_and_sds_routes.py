from __future__ import annotations

import httpx
import pytest

from skriptoteket.application.curated_apps.reagent_prep_chef import (
    ReagentPrepChefChemicalOption,
    ReagentPrepChefChemicalsResult,
)
from skriptoteket.domain.identity.models import User
from skriptoteket.web.api.v1 import apps_reagent_prep_chef as reagent_prep_chef_api
from tests.unit.web.reagent_prep_chef.test_support import (
    StubActorHandler,
    StubSdsStore,
)


@pytest.mark.asyncio
async def test_list_chemicals_requires_auth(client: httpx.AsyncClient) -> None:
    response = await client.get(f"/api/v1/apps/{reagent_prep_chef_api.APP_ID}/chemicals")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_chemicals_returns_items(
    client: httpx.AsyncClient,
    auth_headers: dict[str, str],
    auth_user: User,
    chemicals_handler: StubActorHandler[ReagentPrepChefChemicalsResult],
) -> None:
    chemicals_handler.set_result(
        ReagentPrepChefChemicalsResult(
            chemicals=[
                ReagentPrepChefChemicalOption(
                    key="NaCl", display_name="Natriumklorid", aliases=["Koksalt"]
                )
            ]
        )
    )

    response = await client.get(
        f"/api/v1/apps/{reagent_prep_chef_api.APP_ID}/chemicals",
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json()["chemicals"][0]["key"] == "NaCl"
    assert chemicals_handler.calls == [auth_user]


@pytest.mark.asyncio
async def test_get_sds_returns_content(
    client: httpx.AsyncClient,
    auth_headers: dict[str, str],
    sds_store: StubSdsStore,
) -> None:
    sds_store.add(
        sds_ref="NaCl",
        pdf_file_name="NaCl.pdf",
        pdf_bytes=b"%PDF-1.4\n%test\n",
    )

    response = await client.get(
        f"/api/v1/apps/{reagent_prep_chef_api.APP_ID}/sds/NaCl",
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/pdf")
    assert "NaCl.pdf" in response.headers["content-disposition"]
    assert response.content.startswith(b"%PDF")
    assert sds_store.calls_pdf == ["NaCl"]


@pytest.mark.asyncio
async def test_get_sds_returns_404_for_missing(
    client: httpx.AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    response = await client.get(
        f"/api/v1/apps/{reagent_prep_chef_api.APP_ID}/sds/Unknown",
        headers=auth_headers,
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_sds_markdown_returns_payload(
    client: httpx.AsyncClient,
    auth_headers: dict[str, str],
    sds_store: StubSdsStore,
) -> None:
    sds_store.add(
        sds_ref="NaCl",
        md_file_name="NaCl.md",
        provider="carlroth",
        revision="undated",
        markdown="# Säkerhetsdatablad\n\n## AVSNITT 1\n",
        pdf_file_name=None,
    )

    response = await client.get(
        f"/api/v1/apps/{reagent_prep_chef_api.APP_ID}/sds/NaCl/markdown",
        headers=auth_headers,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["sds_ref"] == "NaCl"
    assert payload["provider"] == "carlroth"
    assert payload["revision"] == "undated"
    assert payload["pdf_available"] is True
    assert payload["markdown"].startswith("# Säkerhetsdatablad")
    assert sds_store.calls_markdown == ["NaCl"]
