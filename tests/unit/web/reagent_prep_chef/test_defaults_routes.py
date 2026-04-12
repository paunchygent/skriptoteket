from __future__ import annotations

from datetime import datetime
from uuid import UUID

import httpx
import pytest

from skriptoteket.application.curated_apps.reagent_prep_chef import (
    ReagentPrepChefDefaultsResult,
    ReagentPrepChefLoadDefaultsRequest,
    ReagentPrepChefPrepRequest,
    ReagentPrepChefSaveDefaultsRequest,
    ReagentPrepChefSaveDefaultsResult,
    ReagentPrepChefUpdateDefaultsRequest,
)
from skriptoteket.application.scripting.vault import VaultFileInfo
from skriptoteket.domain.identity.models import User
from skriptoteket.domain.scripting.file_refs import build_vault_file_ref
from skriptoteket.web.api.v1 import apps_reagent_prep_chef as reagent_prep_chef_api
from tests.unit.web.reagent_prep_chef.test_support import (
    StubActorCommandHandler,
)


@pytest.mark.asyncio
async def test_get_defaults_requires_auth(client: httpx.AsyncClient) -> None:
    response = await client.get(f"/api/v1/apps/{reagent_prep_chef_api.APP_ID}/defaults")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_update_defaults_rejects_stale_csrf_without_signed_context(
    client: httpx.AsyncClient,
) -> None:
    response = await client.put(
        f"/api/v1/apps/{reagent_prep_chef_api.APP_ID}/defaults",
        headers={"X-CSRF-Token": "stale-local-csrf"},
        json={"expected_state_rev": 0, "defaults": None},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_update_defaults_returns_defaults(
    client: httpx.AsyncClient,
    auth_headers: dict[str, str],
    auth_user: User,
    update_defaults_handler: StubActorCommandHandler[
        ReagentPrepChefUpdateDefaultsRequest, ReagentPrepChefDefaultsResult
    ],
    now: datetime,
) -> None:
    defaults = ReagentPrepChefPrepRequest(
        chemical_formula="NaCl",
        target_molarity="0.1",
        vol_per_group_ml="50",
        student_count=30,
        students_per_group=2,
        safety_factor="0.10",
        source_type="solid",
        stock_molarity=None,
        solute_purity="1.0",
    )

    update_defaults_handler.set_result(
        ReagentPrepChefDefaultsResult(defaults=defaults, state_rev=1)
    )

    response = await client.put(
        f"/api/v1/apps/{reagent_prep_chef_api.APP_ID}/defaults",
        headers=auth_headers,
        json={
            "expected_state_rev": 0,
            "defaults": {
                "chemical_formula": "NaCl",
                "target_molarity": "0.1",
                "vol_per_group_ml": "50",
                "student_count": 30,
                "students_per_group": 2,
                "safety_factor": "0.10",
                "source_type": "solid",
                "solute_purity": "1.0",
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["defaults"]["chemical_formula"] == "NaCl"
    assert payload["state_rev"] == 1
    assert update_defaults_handler.calls
    actor_called, command_called = update_defaults_handler.calls[0]
    assert actor_called == auth_user
    assert command_called.expected_state_rev == 0
    assert command_called.defaults is not None
    assert command_called.defaults.chemical_formula == "NaCl"


@pytest.mark.asyncio
async def test_save_defaults_rejects_stale_csrf_without_signed_context(
    client: httpx.AsyncClient,
) -> None:
    response = await client.post(
        f"/api/v1/apps/{reagent_prep_chef_api.APP_ID}/save-defaults",
        headers={"X-CSRF-Token": "stale-local-csrf"},
        json={
            "defaults": {
                "chemical_formula": "NaCl",
                "target_molarity": "0.1",
                "vol_per_group_ml": "50",
                "student_count": 30,
                "students_per_group": 2,
                "safety_factor": "0.10",
                "source_type": "solid",
                "solute_purity": "1.0",
            },
            "name": "default.json",
        },
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_save_defaults_returns_file_ref(
    client: httpx.AsyncClient,
    auth_headers: dict[str, str],
    auth_user: User,
    save_defaults_handler: StubActorCommandHandler[
        ReagentPrepChefSaveDefaultsRequest, ReagentPrepChefSaveDefaultsResult
    ],
    now: datetime,
) -> None:
    file_id = UUID("00000000-0000-0000-0000-0000000000ab")
    save_defaults_handler.set_result(
        ReagentPrepChefSaveDefaultsResult(
            file=VaultFileInfo(
                id=file_id,
                ref=build_vault_file_ref(file_id=file_id),
                name="default.json",
                bytes=123,
                created_at=now,
                deleted_at=None,
            )
        )
    )

    response = await client.post(
        f"/api/v1/apps/{reagent_prep_chef_api.APP_ID}/save-defaults",
        headers=auth_headers,
        json={
            "defaults": {
                "chemical_formula": "NaCl",
                "target_molarity": "0.1",
                "vol_per_group_ml": "50",
                "student_count": 30,
                "students_per_group": 2,
                "safety_factor": "0.10",
                "source_type": "solid",
                "solute_purity": "1.0",
            },
            "name": "default.json",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["file"]["name"] == "default.json"
    assert payload["file"]["ref"].startswith("vault:")
    assert save_defaults_handler.calls
    actor_called, command_called = save_defaults_handler.calls[0]
    assert actor_called == auth_user
    assert command_called.name == "default.json"


@pytest.mark.asyncio
async def test_load_defaults_rejects_stale_csrf_without_signed_context(
    client: httpx.AsyncClient,
) -> None:
    response = await client.post(
        f"/api/v1/apps/{reagent_prep_chef_api.APP_ID}/load-defaults",
        headers={"X-CSRF-Token": "stale-local-csrf"},
        json={"expected_state_rev": 0, "file_id": "00000000-0000-0000-0000-0000000000ab"},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_load_defaults_returns_defaults(
    client: httpx.AsyncClient,
    auth_headers: dict[str, str],
    auth_user: User,
    load_defaults_handler: StubActorCommandHandler[
        ReagentPrepChefLoadDefaultsRequest, ReagentPrepChefDefaultsResult
    ],
    now: datetime,
) -> None:
    defaults = ReagentPrepChefPrepRequest(
        chemical_formula="NaCl",
        target_molarity="0.1",
        vol_per_group_ml="50",
        student_count=30,
        students_per_group=2,
        safety_factor="0.10",
        source_type="solid",
        stock_molarity=None,
        solute_purity="1.0",
    )
    load_defaults_handler.set_result(ReagentPrepChefDefaultsResult(defaults=defaults, state_rev=1))

    response = await client.post(
        f"/api/v1/apps/{reagent_prep_chef_api.APP_ID}/load-defaults",
        headers=auth_headers,
        json={"expected_state_rev": 0, "file_id": "00000000-0000-0000-0000-0000000000ab"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["defaults"]["chemical_formula"] == "NaCl"
    assert payload["state_rev"] == 1
    assert load_defaults_handler.calls
    actor_called, command_called = load_defaults_handler.calls[0]
    assert actor_called == auth_user
    assert command_called.file_id == UUID("00000000-0000-0000-0000-0000000000ab")
