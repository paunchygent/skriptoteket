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
from skriptoteket.domain.identity.models import User
from skriptoteket.domain.scripting.file_refs import build_vault_file_ref
from skriptoteket.web.api.v1 import apps_reagent_prep_chef as reagent_prep_chef_api
from tests.unit.web.reagent_prep_chef.test_support import (
    StubActorCommandHandler,
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
async def test_prep_rejects_stale_csrf_without_signed_context(
    client: httpx.AsyncClient,
    prep_handler: StubActorCommandHandler[ReagentPrepChefPrepRequest, ReagentPrepChefPrepResult],
) -> None:
    response = await client.post(
        f"/api/v1/apps/{reagent_prep_chef_api.APP_ID}/prep",
        headers={"X-CSRF-Token": "stale-local-csrf"},
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

    assert response.status_code == 401
    assert prep_handler.calls == []


@pytest.mark.asyncio
async def test_prep_success_returns_sheet(
    client: httpx.AsyncClient,
    auth_headers: dict[str, str],
    auth_user: User,
    prep_handler: StubActorCommandHandler[ReagentPrepChefPrepRequest, ReagentPrepChefPrepResult],
    now: datetime,
) -> None:
    prep_handler.set_result(_sample_prep_result(now=now))

    response = await client.post(
        f"/api/v1/apps/{reagent_prep_chef_api.APP_ID}/prep",
        headers=auth_headers,
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
    assert actor_called == auth_user
    assert command_called.chemical_formula == "NaCl"


@pytest.mark.asyncio
async def test_export_pdf_returns_download(
    client: httpx.AsyncClient,
    auth_headers: dict[str, str],
    export_pdf_handler: StubActorCommandHandler[ReagentPrepChefPrepRequest, bytes],
) -> None:
    export_pdf_handler.set_result(b"%PDF-1.4 stub")

    response = await client.post(
        f"/api/v1/apps/{reagent_prep_chef_api.APP_ID}/export-pdf",
        headers=auth_headers,
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
async def test_save_pdf_rejects_stale_csrf_without_signed_context(
    client: httpx.AsyncClient,
) -> None:
    response = await client.post(
        f"/api/v1/apps/{reagent_prep_chef_api.APP_ID}/save-pdf",
        headers={"X-CSRF-Token": "stale-local-csrf"},
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

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_save_pdf_returns_vault_file_info(
    client: httpx.AsyncClient,
    auth_headers: dict[str, str],
    save_pdf_handler: StubActorCommandHandler[
        ReagentPrepChefSavePdfRequest, ReagentPrepChefSavePdfResult
    ],
    now: datetime,
) -> None:
    file_id = UUID("00000000-0000-0000-0000-000000000001")

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

    response = await client.post(
        f"/api/v1/apps/{reagent_prep_chef_api.APP_ID}/save-pdf",
        headers=auth_headers,
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
