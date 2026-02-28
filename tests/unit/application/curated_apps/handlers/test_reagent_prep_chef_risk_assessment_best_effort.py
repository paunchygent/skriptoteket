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
    ClpBand,
    HazardEntry,
    HazardSdsData,
)
from skriptoteket.domain.curated_apps.reagent_prep_chef.risk_assessment import (
    RiskTemplate,
    RiskTemplates,
)
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
        now = datetime(2026, 2, 18, 12, 0, 0, tzinfo=timezone.utc)
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
        now = datetime(2026, 2, 18, 12, 0, 1, tzinfo=timezone.utc)
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


class StubSdsIndexStore:
    def __init__(
        self, *, sds_data: HazardSdsData | None, raise_on_ensure: Exception | None = None
    ) -> None:
        self._sds_data = sds_data
        self._raise = raise_on_ensure
        self.calls: list[dict[str, object]] = []

    async def ensure(
        self,
        *,
        hazard: HazardEntry,
        allow_fetch: bool = True,
        require_complete: bool = True,
    ) -> HazardSdsData:
        self.calls.append(
            {
                "hazard_key": hazard.key,
                "allow_fetch": allow_fetch,
                "require_complete": require_complete,
            }
        )
        if self._raise is not None:
            raise self._raise
        if self._sds_data is None:
            raise AssertionError("StubSdsIndexStore configured without sds_data but no exception.")
        return self._sds_data

    def get_cached(self, *, sds_ref: str) -> tuple[str, bytes, str]:  # noqa: ARG002
        raise AssertionError("Not used by these tests.")


def _prep_result(*, formula_clean: str) -> ReagentPrepChefPrepResult:
    sheet = ReagentPrepChefPrepSheet.model_validate(
        {
            "meta": {
                "generated_at": "2026-02-18T12:00:00Z",
                "app_version": "test",
            },
            "logistics": {
                "total_groups": 1,
                "total_volume_ml": "50.0",
                "base_total_volume_ml": "50.0",
                "safety_factor_pct": "10",
            },
            "chemistry": {
                "source_type": "solid",
                "formula_clean": formula_clean,
                "molar_mass_g_mol": "58.44",
                "moles_required": "0.1",
                "target_molarity": "0.10",
                "solute_purity": "1.0",
                "stock_molarity": None,
                "mass_g": "1.0",
                "stock_volume_ml": None,
                "diluent_volume_ml": None,
            },
            "instructions": ["Step 1"],
            "warnings": [],
            "safety": {
                "level": "curated",
                "message": None,
                "display_name": "Salt",
                "hazard_codes": [],
                "ppe": [],
                "disposal": None,
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
        default_severity=2,
        default_likelihood=2,
        measures=("Hantera glas varsamt",),
    )
    return RiskTemplates(
        risk_levels=(),
        hazard_risks=(),
        generic_risks=(generic,),
    )


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
                severity=None,
                likelihood=None,
                measures=None,
                confirmed=True,
            )
        ],
    )
    return ReagentPrepChefRiskAssessmentRequest(
        prep=prep, expected_state_rev=0, inputs=inputs, reset=False
    )


@pytest.mark.asyncio
async def test_risk_draft_best_effort_sets_missing_flags_and_export_gate_for_partial_sds() -> None:
    actor = make_user()
    prep_result = _prep_result(formula_clean="NaCl")
    hazard_entry = HazardEntry(key="NaCl", display_name="Salt")
    templates = _risk_templates()
    sds_data = HazardSdsData(
        sds_ref="NaCl",
        hazard_codes=("H302",),
        pictograms=(),
        signal_word="warning",
        density_g_ml=None,
        clp_bands=(),
        incompatibilities=(),
        exothermicity=None,
        reaction_notes=(),
        sources=(),
    )
    handler = ReagentPrepChefRiskAssessmentHandler(
        prep=StubPrepHandler(result=prep_result),
        hazards=StubHazardStore(hazard=hazard_entry),
        risk_templates=StubRiskTemplatesStore(templates=templates),
        sds_index=StubSdsIndexStore(sds_data=sds_data),
        sessions=StubToolSessions(),
        uow=NoopUow(),
        id_generator=StubIdGenerator(),
    )

    context = ReagentPrepChefRiskContext(
        scope="Demo",
        location=None,
        participants="9A",
        approver="Teacher",
        assessment_date=date(2026, 2, 18),
        next_review_date=date(2026, 6, 18),
        local_routines=None,
    )
    result = await handler.handle(
        actor=actor,
        command=_risk_command(formula="NaCl", context=context),
        allow_fetch=True,
        require_complete=False,
    )

    assert result.draft.sds.pdf_available is True
    assert result.draft.sds.sds_ref == "NaCl"
    assert result.draft.sds.missing_flags == [
        "sds_density_missing",
        "sds_clp_bands_missing",
        "sds_heuristics_missing",
    ]
    assert result.draft.clp.hazard_codes == ["H302"]
    assert result.draft.clp.signal_word == "warning"
    assert result.draft.clp.notes == ["SCL saknas i SDS; visar SDS-koder (best effort)."]
    assert result.draft.missing_flags == [
        "sds_density_missing",
        "sds_clp_bands_missing",
        "sds_heuristics_missing",
        "heuristics_unavailable",
    ]
    assert result.draft.export_gate.ready is True
    assert result.draft.export_gate.missing_confirmations == []
    assert result.draft.export_gate.missing_context_fields == []
    assert result.draft.export_gate.missing_data_flags == []


@pytest.mark.asyncio
async def test_risk_draft_best_effort_sets_pdf_missing_when_sds_unavailable() -> None:
    actor = make_user()
    prep_result = _prep_result(formula_clean="NaCl")
    hazard_entry = HazardEntry(key="NaCl", display_name="Salt")
    templates = _risk_templates()

    handler = ReagentPrepChefRiskAssessmentHandler(
        prep=StubPrepHandler(result=prep_result),
        hazards=StubHazardStore(hazard=hazard_entry),
        risk_templates=StubRiskTemplatesStore(templates=templates),
        sds_index=StubSdsIndexStore(sds_data=None, raise_on_ensure=RuntimeError("no sds")),
        sessions=StubToolSessions(),
        uow=NoopUow(),
        id_generator=StubIdGenerator(),
    )

    context = ReagentPrepChefRiskContext(
        scope="Demo",
        location=None,
        participants="9A",
        approver="Teacher",
        assessment_date=date(2026, 2, 18),
        next_review_date=date(2026, 6, 18),
        local_routines=None,
    )
    result = await handler.handle(
        actor=actor,
        command=_risk_command(formula="NaCl", context=context),
        allow_fetch=True,
        require_complete=False,
    )

    assert result.draft.sds.pdf_available is False
    assert result.draft.sds.sds_ref is None
    assert result.draft.sds.missing_flags == ["sds_pdf_missing"]
    assert result.draft.missing_flags == ["sds_pdf_missing", "heuristics_unavailable"]
    assert result.draft.export_gate.ready is True
    assert result.draft.export_gate.missing_context_fields == []
    assert result.draft.export_gate.missing_confirmations == []
    assert result.draft.export_gate.missing_data_flags == []


@pytest.mark.asyncio
async def test_risk_draft_sets_clp_unavailable_for_target_when_bands_do_not_match_target() -> None:
    actor = make_user()
    prep_result = _prep_result(formula_clean="NaCl")
    hazard_entry = HazardEntry(key="NaCl", display_name="Salt")
    templates = _risk_templates()
    sds_data = HazardSdsData(
        sds_ref="NaCl",
        hazard_codes=("H302",),
        pictograms=(),
        signal_word="warning",
        density_g_ml=Decimal("1.0"),
        clp_bands=(
            ClpBand(
                min_molarity=Decimal("0.01"),
                max_molarity=Decimal("0.10"),
                hazard_codes=("H302",),
                pictograms=(),
                signal_word="warning",
                notes=(),
            ),
        ),
        incompatibilities=("Acids",),
        exothermicity=None,
        reaction_notes=(),
        sources=(),
    )
    handler = ReagentPrepChefRiskAssessmentHandler(
        prep=StubPrepHandler(result=prep_result),
        hazards=StubHazardStore(hazard=hazard_entry),
        risk_templates=StubRiskTemplatesStore(templates=templates),
        sds_index=StubSdsIndexStore(sds_data=sds_data),
        sessions=StubToolSessions(),
        uow=NoopUow(),
        id_generator=StubIdGenerator(),
    )

    context = ReagentPrepChefRiskContext(
        scope="Demo",
        location=None,
        participants="9A",
        approver="Teacher",
        assessment_date=date(2026, 2, 18),
        next_review_date=date(2026, 6, 18),
        local_routines=None,
    )
    result = await handler.handle(
        actor=actor,
        command=_risk_command(formula="NaCl", context=context),
        allow_fetch=True,
        require_complete=False,
    )

    assert result.draft.missing_flags == ["clp_unavailable_for_target"]
    assert result.draft.clp.hazard_codes == ["H302"]
    assert result.draft.clp.signal_word == "warning"
    assert result.draft.clp.notes == [
        "SCL saknas för vald koncentration; visar SDS-koder (best effort)."
    ]
    assert result.draft.export_gate.ready is True
    assert result.draft.export_gate.missing_data_flags == []


@pytest.mark.asyncio
async def test_risk_draft_allows_export_when_sds_has_hazard_codes_but_no_bands() -> None:
    actor = make_user()
    prep_result = _prep_result(formula_clean="NaCl")
    hazard_entry = HazardEntry(key="NaCl", display_name="Salt")
    templates = _risk_templates()
    sds_data = HazardSdsData(
        sds_ref="NaCl",
        hazard_codes=("H302",),
        pictograms=("GHS07",),
        signal_word="warning",
        density_g_ml=Decimal("1.0"),
        clp_bands=(),
        incompatibilities=("Acids",),
        exothermicity=None,
        reaction_notes=(),
        sources=(),
    )
    handler = ReagentPrepChefRiskAssessmentHandler(
        prep=StubPrepHandler(result=prep_result),
        hazards=StubHazardStore(hazard=hazard_entry),
        risk_templates=StubRiskTemplatesStore(templates=templates),
        sds_index=StubSdsIndexStore(sds_data=sds_data),
        sessions=StubToolSessions(),
        uow=NoopUow(),
        id_generator=StubIdGenerator(),
    )

    context = ReagentPrepChefRiskContext(
        scope="Demo",
        location=None,
        participants="9A",
        approver="Teacher",
        assessment_date=date(2026, 2, 18),
        next_review_date=date(2026, 6, 18),
        local_routines=None,
    )
    result = await handler.handle(
        actor=actor,
        command=_risk_command(formula="NaCl", context=context),
        allow_fetch=True,
        require_complete=False,
    )

    assert result.draft.sds.pdf_available is True
    assert result.draft.sds.missing_flags == ["sds_clp_bands_missing"]
    assert result.draft.clp.hazard_codes == ["H302"]
    assert result.draft.clp.pictograms == ["GHS07"]
    assert result.draft.clp.signal_word == "warning"
    assert result.draft.clp.notes == ["SCL saknas i SDS; visar SDS-koder (best effort)."]
    assert result.draft.export_gate.ready is True
    assert result.draft.export_gate.missing_data_flags == []
