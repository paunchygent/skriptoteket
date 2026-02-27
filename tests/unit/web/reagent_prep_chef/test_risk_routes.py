from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

import httpx
import pytest

from skriptoteket.application.curated_apps.reagent_prep_chef import (
    ReagentPrepChefChemistry,
    ReagentPrepChefChemistryHeuristics,
    ReagentPrepChefClpClassification,
    ReagentPrepChefLogistics,
    ReagentPrepChefMeta,
    ReagentPrepChefPrepSheet,
    ReagentPrepChefRiskAssessmentDraft,
    ReagentPrepChefRiskAssessmentRequest,
    ReagentPrepChefRiskAssessmentResult,
    ReagentPrepChefRiskContext,
    ReagentPrepChefRiskExportGate,
    ReagentPrepChefRiskItem,
    ReagentPrepChefRiskRating,
    ReagentPrepChefSafety,
    ReagentPrepChefSavePdfResult,
    ReagentPrepChefSdsSnapshot,
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
    rating = ReagentPrepChefRiskRating(severity=2, likelihood=2, score=4, level="low")
    draft = ReagentPrepChefRiskAssessmentDraft(
        sheet=sheet,
        sds=ReagentPrepChefSdsSnapshot(
            sds_ref="NaCl",
            pdf_available=True,
            missing_flags=[],
            sources=[],
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
        clp=ReagentPrepChefClpClassification(
            hazard_codes=[],
            pictograms=[],
            signal_word=None,
            notes=[],
        ),
        heuristics=ReagentPrepChefChemistryHeuristics(
            incompatibilities=[],
            exothermicity=None,
            reaction_notes=[],
        ),
        risks=[
            ReagentPrepChefRiskItem(
                id="glass_breakage",
                title="Glas går sönder",
                description=None,
                hazard_codes=[],
                measures=["Hantera glas varsamt"],
                computed=rating,
                final=rating,
                confirmed=True,
            )
        ],
        requires_confirmation=False,
        missing_confirmations=[],
        missing_flags=[],
        export_gate=ReagentPrepChefRiskExportGate(
            ready=True,
            missing_confirmations=[],
            missing_context_fields=[],
            missing_data_flags=[],
        ),
    )
    return ReagentPrepChefRiskAssessmentResult(draft=draft, warnings=[], state_rev=1)


@pytest.mark.asyncio
async def test_risk_assessment_requires_csrf(
    client: httpx.AsyncClient,
    settings: Settings,
    current_user_provider: StubCurrentUserProvider,
    sessions: StubSessionRepository,
    risk_assessment_handler: StubActorCommandHandler[
        ReagentPrepChefRiskAssessmentRequest, ReagentPrepChefRiskAssessmentResult
    ],
    now: datetime,
) -> None:
    user = make_user(role=Role.USER)
    session = make_session(user_id=user.id, now=now)

    current_user_provider.user = user
    sessions.sessions[session.id] = session

    client.cookies.set(settings.SESSION_COOKIE_NAME, str(session.id))
    response = await client.post(
        f"/api/v1/apps/{reagent_prep_chef_api.APP_ID}/risk-assessment",
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

    assert response.status_code == 403
    assert risk_assessment_handler.calls == []


@pytest.mark.asyncio
async def test_risk_assessment_returns_draft(
    client: httpx.AsyncClient,
    settings: Settings,
    current_user_provider: StubCurrentUserProvider,
    sessions: StubSessionRepository,
    risk_assessment_handler: StubActorCommandHandler[
        ReagentPrepChefRiskAssessmentRequest, ReagentPrepChefRiskAssessmentResult
    ],
    now: datetime,
) -> None:
    user = make_user(role=Role.USER)
    session = make_session(user_id=user.id, now=now)

    current_user_provider.user = user
    sessions.sessions[session.id] = session
    risk_assessment_handler.set_result(_sample_risk_result(now=now))

    client.cookies.set(settings.SESSION_COOKIE_NAME, str(session.id))
    response = await client.post(
        f"/api/v1/apps/{reagent_prep_chef_api.APP_ID}/risk-assessment",
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
    settings: Settings,
    current_user_provider: StubCurrentUserProvider,
    sessions: StubSessionRepository,
    export_risk_pdf_handler: StubActorCommandHandler[ReagentPrepChefRiskAssessmentRequest, bytes],
    now: datetime,
) -> None:
    user = make_user(role=Role.USER)
    session = make_session(user_id=user.id, now=now)

    current_user_provider.user = user
    sessions.sessions[session.id] = session
    export_risk_pdf_handler.set_result(b"%PDF-1.4 stub")

    client.cookies.set(settings.SESSION_COOKIE_NAME, str(session.id))
    response = await client.post(
        f"/api/v1/apps/{reagent_prep_chef_api.APP_ID}/export-risk-pdf",
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
            "expected_state_rev": 0,
            "reset": False,
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/pdf")
    assert "riskbedomning.pdf" in response.headers["content-disposition"]
    assert response.content == b"%PDF-1.4 stub"
    assert export_risk_pdf_handler.calls


@pytest.mark.asyncio
async def test_save_risk_pdf_returns_vault_ref(
    client: httpx.AsyncClient,
    settings: Settings,
    current_user_provider: StubCurrentUserProvider,
    sessions: StubSessionRepository,
    save_risk_pdf_handler: StubActorCommandHandler[
        ReagentPrepChefRiskAssessmentRequest, ReagentPrepChefSavePdfResult
    ],
    now: datetime,
) -> None:
    user = make_user(role=Role.USER)
    session = make_session(user_id=user.id, now=now)

    file_id = UUID("00000000-0000-0000-0000-000000000002")
    save_risk_pdf_handler.set_result(
        ReagentPrepChefSavePdfResult(
            file=VaultFileInfo(
                id=file_id,
                ref=build_vault_file_ref(file_id=file_id),
                name="riskbedomning.pdf",
                bytes=123,
                created_at=now,
                deleted_at=None,
            )
        )
    )

    current_user_provider.user = user
    sessions.sessions[session.id] = session

    client.cookies.set(settings.SESSION_COOKIE_NAME, str(session.id))
    response = await client.post(
        f"/api/v1/apps/{reagent_prep_chef_api.APP_ID}/save-risk-pdf",
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
            "expected_state_rev": 0,
            "reset": False,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["file"]["name"] == "riskbedomning.pdf"
    assert payload["file"]["ref"].startswith("vault:")
    assert save_risk_pdf_handler.calls
