from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID

import pytest

from skriptoteket.application.curated_apps.handlers.reagent_prep_chef_risk_assessment import (
    ReagentPrepChefRiskAssessmentHandler,
)
from skriptoteket.application.curated_apps.reagent_prep_chef import (
    ReagentPrepChefPrepRequest,
    ReagentPrepChefPrepResult,
    ReagentPrepChefPrepSheet,
    ReagentPrepChefRiskAssessmentInputs,
    ReagentPrepChefRiskAssessmentRequest,
    ReagentPrepChefRiskContext,
    ReagentPrepChefRiskItemOverride,
)
from skriptoteket.domain.curated_apps.reagent_prep_chef.models import (
    HazardEntry,
    SdsCorpusEntry,
)
from skriptoteket.domain.curated_apps.reagent_prep_chef.risk_assessment import (
    RiskTemplate,
    RiskTemplates,
)
from skriptoteket.domain.errors import not_found
from skriptoteket.domain.scripting.tool_sessions import ToolSession
from tests.fixtures.identity_fixtures import make_user


class NoopUow:
    async def __aenter__(self) -> "NoopUow":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
        return None


class StubIdGenerator:
    def __init__(self) -> None:
        self._ids = iter(
            [
                UUID("00000000-0000-0000-0000-000000000001"),
                UUID("00000000-0000-0000-0000-000000000002"),
            ]
        )

    def new_uuid(self) -> UUID:
        return next(self._ids)


class StubToolSessions:
    def __init__(self) -> None:
        self.session: ToolSession | None = None

    async def get(self, *, tool_id: UUID, user_id: UUID, context: str) -> ToolSession | None:  # noqa: ARG002
        return self.session

    async def get_or_create(
        self,
        *,
        session_id: UUID,
        tool_id: UUID,
        user_id: UUID,
        context: str,
    ) -> ToolSession:
        if self.session is not None:
            return self.session
        now = datetime(2026, 3, 4, 12, 0, 0, tzinfo=timezone.utc)
        self.session = ToolSession(
            id=session_id,
            tool_id=tool_id,
            user_id=user_id,
            context=context,
            state={},
            state_rev=0,
            created_at=now,
            updated_at=now,
        )
        return self.session

    async def update_state(
        self,
        *,
        tool_id: UUID,  # noqa: ARG002
        user_id: UUID,  # noqa: ARG002
        context: str,  # noqa: ARG002
        expected_state_rev: int,
        state: dict,
    ) -> ToolSession:
        if self.session is None:
            raise AssertionError("Expected get_or_create() before update_state().")
        if expected_state_rev != self.session.state_rev:
            raise AssertionError("Unexpected expected_state_rev in test.")
        now = datetime(2026, 3, 4, 12, 0, 1, tzinfo=timezone.utc)
        self.session = self.session.model_copy(
            update={
                "state": state,
                "state_rev": self.session.state_rev + 1,
                "updated_at": now,
            }
        )
        return self.session

    async def clear_state(
        self,
        *,
        tool_id: UUID,  # noqa: ARG002
        user_id: UUID,  # noqa: ARG002
        context: str,  # noqa: ARG002
    ) -> ToolSession:
        raise AssertionError("Not used by these tests.")


class StubPrepHandler:
    def __init__(self, *, result: ReagentPrepChefPrepResult) -> None:
        self._result = result

    async def handle(self, *, actor, command) -> ReagentPrepChefPrepResult:  # noqa: ANN001, ARG002
        return self._result


class StubHazardStore:
    def __init__(self, *, hazard: HazardEntry) -> None:
        self._hazard = hazard

    def lookup(self, *, formula_clean: str) -> HazardEntry | None:
        return self._hazard if formula_clean == self._hazard.key else None

    def list_all(self) -> list[HazardEntry]:
        return [self._hazard]


class StubRiskTemplatesStore:
    def __init__(self, *, templates: RiskTemplates) -> None:
        self._templates = templates

    def get(self) -> RiskTemplates:
        return self._templates


class StubSdsStore:
    def __init__(self, *, entry: SdsCorpusEntry | None) -> None:
        self._entry = entry

    def get_entry(self, *, sds_ref: str) -> SdsCorpusEntry:  # noqa: ARG002
        if self._entry is None:
            raise not_found("SDS", sds_ref)
        return self._entry

    def get_markdown(self, *, sds_ref: str):  # noqa: ANN001
        raise AssertionError("Not used by these tests.")

    def get_pdf(self, *, sds_ref: str):  # noqa: ANN001
        raise AssertionError("Not used by these tests.")


def _prep_result() -> ReagentPrepChefPrepResult:
    sheet = ReagentPrepChefPrepSheet.model_validate(
        {
            "meta": {"generated_at": "2026-03-04T12:00:00+00:00", "app_version": "test"},
            "logistics": {
                "total_groups": 1,
                "total_volume_ml": "50.0",
                "base_total_volume_ml": "50.0",
                "safety_factor_pct": "10",
            },
            "chemistry": {
                "source_type": "solid",
                "formula_clean": "NaCl",
                "molar_mass_g_mol": "58.44",
                "moles_required": "0.025",
                "target_molarity": "0.50",
                "solute_purity": "1.0",
                "stock_molarity": None,
                "mass_g": "1.46",
                "stock_volume_ml": None,
                "diluent_volume_ml": None,
            },
            "instructions": ["Step 1"],
            "warnings": [],
            "safety": {
                "level": "curated",
                "message": None,
                "display_name": "Salt",
                "hazard_codes": ["H319"],
                "ppe": ["Skyddsglasögon"],
                "disposal": "Följ lokala rutiner och SDS.",
                "notes": [],
            },
        }
    )
    return ReagentPrepChefPrepResult(sheet=sheet)


def _risk_templates() -> RiskTemplates:
    generic = RiskTemplate(
        id="glass_breakage",
        title="Glas går sönder",
        hazard_codes_any=(),
        measures=("Hantera glas varsamt",),
    )
    hazard_specific = RiskTemplate(
        id="eye_contact",
        title="Stänk i ögon",
        hazard_codes_any=("H319",),
        measures=("Skyddsglasögon",),
    )
    return RiskTemplates(hazard_risks=(hazard_specific,), generic_risks=(generic,))


def _risk_command(
    *, formula: str, context: ReagentPrepChefRiskContext
) -> ReagentPrepChefRiskAssessmentRequest:
    prep = ReagentPrepChefPrepRequest(
        chemical_formula=formula,
        target_molarity=Decimal("0.50"),
        vol_per_group_ml=Decimal("50"),
        student_count=2,
        students_per_group=2,
        safety_factor=Decimal("0.10"),
        source_type="solid",
        solute_purity=Decimal("1.0"),
    )
    inputs = ReagentPrepChefRiskAssessmentInputs(
        context=context,
        overrides=[
            ReagentPrepChefRiskItemOverride(
                id="glass_breakage",
                measures=["Använd borste och skyffel"],
                confirmed=True,
            )
        ],
    )
    return ReagentPrepChefRiskAssessmentRequest(
        prep=prep, expected_state_rev=0, inputs=inputs, reset=False
    )


@pytest.mark.asyncio
async def test_risk_draft_sets_sds_snapshot_when_entry_exists() -> None:
    actor = make_user()
    prep = StubPrepHandler(result=_prep_result())
    hazard = HazardEntry(key="NaCl", display_name="Salt", hazard_codes=("H319",))
    hazards = StubHazardStore(hazard=hazard)
    templates = StubRiskTemplatesStore(templates=_risk_templates())
    sds_store = StubSdsStore(
        entry=SdsCorpusEntry(
            sds_ref="NaCl",
            key="NaCl",
            md_file_name="NaCl__carlroth__undated.md",
            provider="carlroth",
            revision="undated",
            pdf_file_name=None,
        )
    )
    sessions = StubToolSessions()
    handler = ReagentPrepChefRiskAssessmentHandler(
        prep=prep,
        hazards=hazards,
        risk_templates=templates,
        sds_store=sds_store,
        sessions=sessions,
        uow=NoopUow(),
        id_generator=StubIdGenerator(),
    )

    command = _risk_command(
        formula="NaCl",
        context=ReagentPrepChefRiskContext(
            scope="Demo",
            participants="9A",
            approver="Lärare",
            assessment_date=date(2026, 3, 4),
            next_review_date=date(2026, 6, 1),
        ),
    )
    result = await handler.handle(actor=actor, command=command)

    assert result.draft.sds.sds_ref == "NaCl"
    assert result.draft.sds.markdown_available is True
    assert result.draft.sds.pdf_available is True
    assert result.draft.sds.provider == "carlroth"
    assert result.draft.sds.revision == "undated"
    assert result.warnings == []


@pytest.mark.asyncio
async def test_risk_draft_warns_when_sds_missing_offline() -> None:
    actor = make_user()
    prep = StubPrepHandler(result=_prep_result())
    hazard = HazardEntry(key="NaCl", display_name="Salt", hazard_codes=("H319",))
    hazards = StubHazardStore(hazard=hazard)
    templates = StubRiskTemplatesStore(templates=_risk_templates())
    sds_store = StubSdsStore(entry=None)
    sessions = StubToolSessions()
    handler = ReagentPrepChefRiskAssessmentHandler(
        prep=prep,
        hazards=hazards,
        risk_templates=templates,
        sds_store=sds_store,
        sessions=sessions,
        uow=NoopUow(),
        id_generator=StubIdGenerator(),
    )

    command = _risk_command(
        formula="NaCl",
        context=ReagentPrepChefRiskContext(
            scope="Demo",
            participants="9A",
            approver="Lärare",
            assessment_date=date(2026, 3, 4),
            next_review_date=date(2026, 6, 1),
        ),
    )
    result = await handler.handle(actor=actor, command=command)

    assert result.draft.sds.sds_ref == "NaCl"
    assert result.draft.sds.markdown_available is False
    assert result.draft.sds.pdf_available is False
    assert "SDS saknas offline" in " ".join(result.warnings)
