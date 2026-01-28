from __future__ import annotations

from datetime import datetime
from uuid import UUID

import httpx
import pytest

from skriptoteket.application.curated_apps.reagent_prep_chef import (
    ReagentPrepChefChemistry,
    ReagentPrepChefLogistics,
    ReagentPrepChefMeta,
    ReagentPrepChefPrepRequest,
    ReagentPrepChefPrepResult,
    ReagentPrepChefPrepSheet,
    ReagentPrepChefSafety,
    ReagentPrepChefSavePdfRequest,
    ReagentPrepChefSavePdfResult,
)
from skriptoteket.application.scripting.vault import VaultFileInfo
from skriptoteket.config import Settings
from skriptoteket.domain.identity.models import Role
from skriptoteket.domain.scripting.file_refs import build_vault_file_ref
from skriptoteket.web.api.v1 import apps_reagent_prep_chef as reagent_prep_chef_api
from tests.fixtures.identity_fixtures import make_session, make_user
from tests.unit.web.reagent_prep_chef.test_support import (
    StubActorCommandHandler,
    StubCurrentUserProvider,
    StubSessionRepository,
)


def _sample_prep_result(*, now: datetime) -> ReagentPrepChefPrepResult:
    sheet = ReagentPrepChefPrepSheet(
        meta=ReagentPrepChefMeta(generated_at=now, app_version="test"),
        logistics=ReagentPrepChefLogistics(
            total_groups=15,
            total_volume_ml="750.0",
            base_total_volume_ml="750.0",
            safety_factor_pct="10",
        ),
        chemistry=ReagentPrepChefChemistry(
            source_type="solid",
            formula_clean="NaCl",
            molar_mass_g_mol="58.44",
            moles_required="0.075",
            target_molarity="0.10",
            solute_purity="1.0",
            stock_molarity=None,
            mass_g="4.39",
            stock_volume_ml=None,
            diluent_volume_ml=None,
        ),
        instructions=["Steg 1"],
        warnings=[],
        safety=ReagentPrepChefSafety(
            level="curated",
            message=None,
            display_name="Natriumklorid",
            hazard_codes=[],
            ppe=["Skyddsglasögon"],
            disposal="Följ lokala rutiner och SDS.",
            notes=[],
        ),
    )
    return ReagentPrepChefPrepResult(sheet=sheet)


@pytest.mark.asyncio
async def test_prep_requires_csrf(
    client: httpx.AsyncClient,
    settings: Settings,
    current_user_provider: StubCurrentUserProvider,
    sessions: StubSessionRepository,
    prep_handler: StubActorCommandHandler[ReagentPrepChefPrepRequest, ReagentPrepChefPrepResult],
    now: datetime,
) -> None:
    user = make_user(role=Role.USER)
    session = make_session(user_id=user.id, now=now)

    current_user_provider.user = user
    sessions.sessions[session.id] = session

    client.cookies.set(settings.SESSION_COOKIE_NAME, str(session.id))
    response = await client.post(
        f"/api/v1/apps/{reagent_prep_chef_api.APP_ID}/prep",
        json={
            "chemical_formula": "NaCl",
            "target_molarity": "0.1",
            "vol_per_group_ml": "50",
            "student_count": 30,
            "students_per_group": 2,
            "safety_factor": "0.10",
            "source_type": "solid",
            "solute_purity": "1.0",
        },
    )

    assert response.status_code == 403
    assert prep_handler.calls == []


@pytest.mark.asyncio
async def test_prep_success_returns_sheet(
    client: httpx.AsyncClient,
    settings: Settings,
    current_user_provider: StubCurrentUserProvider,
    sessions: StubSessionRepository,
    prep_handler: StubActorCommandHandler[ReagentPrepChefPrepRequest, ReagentPrepChefPrepResult],
    now: datetime,
) -> None:
    user = make_user(role=Role.USER)
    session = make_session(user_id=user.id, now=now)

    current_user_provider.user = user
    sessions.sessions[session.id] = session
    prep_handler.set_result(_sample_prep_result(now=now))

    client.cookies.set(settings.SESSION_COOKIE_NAME, str(session.id))
    response = await client.post(
        f"/api/v1/apps/{reagent_prep_chef_api.APP_ID}/prep",
        headers={"X-CSRF-Token": session.csrf_token},
        json={
            "chemical_formula": "NaCl",
            "target_molarity": "0.1",
            "vol_per_group_ml": "50",
            "student_count": 30,
            "students_per_group": 2,
            "safety_factor": "0.10",
            "source_type": "solid",
            "solute_purity": "1.0",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["sheet"]["logistics"]["total_groups"] == 15
    assert payload["sheet"]["chemistry"]["formula_clean"] == "NaCl"
    assert payload["sheet"]["safety"]["level"] == "curated"
    assert prep_handler.calls
    actor_called, command_called = prep_handler.calls[0]
    assert actor_called == user
    assert command_called.chemical_formula == "NaCl"


@pytest.mark.asyncio
async def test_export_pdf_returns_download(
    client: httpx.AsyncClient,
    settings: Settings,
    current_user_provider: StubCurrentUserProvider,
    sessions: StubSessionRepository,
    export_pdf_handler: StubActorCommandHandler[ReagentPrepChefPrepRequest, bytes],
    now: datetime,
) -> None:
    user = make_user(role=Role.USER)
    session = make_session(user_id=user.id, now=now)

    current_user_provider.user = user
    sessions.sessions[session.id] = session
    export_pdf_handler.set_result(b"%PDF-1.4 stub")

    client.cookies.set(settings.SESSION_COOKIE_NAME, str(session.id))
    response = await client.post(
        f"/api/v1/apps/{reagent_prep_chef_api.APP_ID}/export-pdf",
        headers={"X-CSRF-Token": session.csrf_token},
        json={
            "chemical_formula": "NaCl",
            "target_molarity": "0.1",
            "vol_per_group_ml": "50",
            "student_count": 30,
            "students_per_group": 2,
            "safety_factor": "0.10",
            "source_type": "solid",
            "solute_purity": "1.0",
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/pdf")
    assert "reagensberedning.pdf" in response.headers["content-disposition"]
    assert response.content == b"%PDF-1.4 stub"
    assert export_pdf_handler.calls


@pytest.mark.asyncio
async def test_save_pdf_requires_csrf(
    client: httpx.AsyncClient,
    settings: Settings,
    current_user_provider: StubCurrentUserProvider,
    sessions: StubSessionRepository,
    now: datetime,
) -> None:
    user = make_user(role=Role.USER)
    session = make_session(user_id=user.id, now=now)

    current_user_provider.user = user
    sessions.sessions[session.id] = session

    client.cookies.set(settings.SESSION_COOKIE_NAME, str(session.id))
    response = await client.post(
        f"/api/v1/apps/{reagent_prep_chef_api.APP_ID}/save-pdf",
        json={
            "prep": {
                "chemical_formula": "NaCl",
                "target_molarity": "0.1",
                "vol_per_group_ml": "50",
                "student_count": 30,
                "students_per_group": 2,
                "safety_factor": "0.10",
                "source_type": "solid",
                "solute_purity": "1.0",
            },
            "name": "NaCl.pdf",
        },
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_save_pdf_returns_vault_file_info(
    client: httpx.AsyncClient,
    settings: Settings,
    current_user_provider: StubCurrentUserProvider,
    sessions: StubSessionRepository,
    save_pdf_handler: StubActorCommandHandler[
        ReagentPrepChefSavePdfRequest, ReagentPrepChefSavePdfResult
    ],
    now: datetime,
) -> None:
    user = make_user(role=Role.USER)
    session = make_session(user_id=user.id, now=now)
    file_id = UUID("00000000-0000-0000-0000-000000000001")

    current_user_provider.user = user
    sessions.sessions[session.id] = session
    save_pdf_handler.set_result(
        ReagentPrepChefSavePdfResult(
            file=VaultFileInfo(
                id=file_id,
                ref=build_vault_file_ref(file_id=file_id),
                name="NaCl.pdf",
                bytes=123,
                created_at=now,
                deleted_at=None,
            )
        )
    )

    client.cookies.set(settings.SESSION_COOKIE_NAME, str(session.id))
    response = await client.post(
        f"/api/v1/apps/{reagent_prep_chef_api.APP_ID}/save-pdf",
        headers={"X-CSRF-Token": session.csrf_token},
        json={
            "prep": {
                "chemical_formula": "NaCl",
                "target_molarity": "0.1",
                "vol_per_group_ml": "50",
                "student_count": 30,
                "students_per_group": 2,
                "safety_factor": "0.10",
                "source_type": "solid",
                "solute_purity": "1.0",
            },
            "name": "NaCl.pdf",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["file"]["name"] == "NaCl.pdf"
    assert payload["file"]["ref"].startswith("vault:")
    assert save_pdf_handler.calls
