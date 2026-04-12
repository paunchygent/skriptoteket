from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

import httpx
import pytest

from skriptoteket.application.curated_apps.reagent_prep_chef import (
    ReagentPrepChefChemistry,
    ReagentPrepChefLogistics,
    ReagentPrepChefMeta,
    ReagentPrepChefPrepSheet,
    ReagentPrepChefRiskAssessmentDraft,
    ReagentPrepChefRiskAssessmentRequest,
    ReagentPrepChefRiskAssessmentResult,
    ReagentPrepChefRiskContext,
    ReagentPrepChefRiskExportGate,
    ReagentPrepChefRiskItem,
    ReagentPrepChefSafety,
    ReagentPrepChefSavePdfResult,
    ReagentPrepChefSdsSnapshot,
)
from skriptoteket.application.scripting.vault import VaultFileInfo
from skriptoteket.domain.scripting.file_refs import build_vault_file_ref
from skriptoteket.web.api.v1 import apps_reagent_prep_chef as reagent_prep_chef_api
from tests.unit.web.reagent_prep_chef.test_support import (
    StubActorCommandHandler,
)


def _sample_risk_result(*, now: datetime) -> ReagentPrepChefRiskAssessmentResult:
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
    draft = ReagentPrepChefRiskAssessmentDraft(
        sheet=sheet,
        sds=ReagentPrepChefSdsSnapshot(
            sds_ref="NaCl",
            markdown_available=True,
            pdf_available=True,
            provider="carlroth",
            revision="undated",
        ),
        context=ReagentPrepChefRiskContext(
            scope="Demo",
            location="Labbet",
            participants="9A",
            approver="Lärare",
            assessment_date=date(2026, 1, 1),
            next_review_date=date(2026, 6, 1),
            local_routines="Följ lokala rutiner.",
        ),
        risks=[
            ReagentPrepChefRiskItem(
                id="glass_breakage",
                title="Glas går sönder",
                description=None,
                hazard_codes=[],
                measures=["Hantera glas varsamt"],
                confirmed=True,
            )
        ],
        requires_confirmation=False,
        missing_confirmations=[],
        export_gate=ReagentPrepChefRiskExportGate(
            ready=True,
            missing_confirmations=[],
            missing_context_fields=[],
        ),
    )
    return ReagentPrepChefRiskAssessmentResult(draft=draft, warnings=[], state_rev=1)


@pytest.mark.asyncio
async def test_risk_assessment_rejects_stale_csrf_without_signed_context(
    client: httpx.AsyncClient,
    risk_assessment_handler: StubActorCommandHandler[
        ReagentPrepChefRiskAssessmentRequest, ReagentPrepChefRiskAssessmentResult
    ],
) -> None:
    response = await client.post(
        f"/api/v1/apps/{reagent_prep_chef_api.APP_ID}/risk-assessment",
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
            "expected_state_rev": 0,
            "reset": False,
        },
    )

    assert response.status_code == 401
    assert risk_assessment_handler.calls == []


@pytest.mark.asyncio
async def test_risk_assessment_returns_draft(
    client: httpx.AsyncClient,
    auth_headers: dict[str, str],
    risk_assessment_handler: StubActorCommandHandler[
        ReagentPrepChefRiskAssessmentRequest, ReagentPrepChefRiskAssessmentResult
    ],
    now: datetime,
) -> None:
    risk_assessment_handler.set_result(_sample_risk_result(now=now))

    response = await client.post(
        f"/api/v1/apps/{reagent_prep_chef_api.APP_ID}/risk-assessment",
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
            "expected_state_rev": 0,
            "reset": False,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["draft"]["sds"]["sds_ref"] == "NaCl"
    assert payload["draft"]["sds"]["pdf_available"] is True
    assert payload["state_rev"] == 1
    assert risk_assessment_handler.calls


@pytest.mark.asyncio
async def test_export_risk_pdf_returns_download(
    client: httpx.AsyncClient,
    auth_headers: dict[str, str],
    export_risk_pdf_handler: StubActorCommandHandler[ReagentPrepChefRiskAssessmentRequest, bytes],
) -> None:
    export_risk_pdf_handler.set_result(b"%PDF-1.4 stub")

    response = await client.post(
        f"/api/v1/apps/{reagent_prep_chef_api.APP_ID}/export-risk-pdf",
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
            "expected_state_rev": 0,
            "reset": False,
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/pdf")
    assert "underlag-riskbedomning.pdf" in response.headers["content-disposition"]
    assert response.content == b"%PDF-1.4 stub"
    assert export_risk_pdf_handler.calls


@pytest.mark.asyncio
async def test_save_risk_pdf_returns_vault_ref(
    client: httpx.AsyncClient,
    auth_headers: dict[str, str],
    save_risk_pdf_handler: StubActorCommandHandler[
        ReagentPrepChefRiskAssessmentRequest, ReagentPrepChefSavePdfResult
    ],
    now: datetime,
) -> None:
    file_id = UUID("00000000-0000-0000-0000-000000000002")
    save_risk_pdf_handler.set_result(
        ReagentPrepChefSavePdfResult(
            file=VaultFileInfo(
                id=file_id,
                ref=build_vault_file_ref(file_id=file_id),
                name="underlag-riskbedomning.pdf",
                bytes=123,
                created_at=now,
                deleted_at=None,
            )
        )
    )

    response = await client.post(
        f"/api/v1/apps/{reagent_prep_chef_api.APP_ID}/save-risk-pdf",
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
            "expected_state_rev": 0,
            "reset": False,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["file"]["name"] == "underlag-riskbedomning.pdf"
    assert payload["file"]["ref"].startswith("vault:")
    assert save_risk_pdf_handler.calls
