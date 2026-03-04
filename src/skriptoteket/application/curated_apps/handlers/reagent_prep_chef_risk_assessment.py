"""Riskbedömning draft handler for the Reagent Prep Chef curated app.

Builds a deterministic, restorable risk assessment draft from:
- the computed prep sheet (via the prep handler),
- repo-owned curated hazards + repo-owned risk templates,
- offline SDS corpus availability (ADR-0067),
- teacher-provided context + confirmations stored in tool_sessions.

No external SDS fetching and no SDS-derived signal extraction
(CLP bands, density, heuristics, risk scoring).
"""

from __future__ import annotations

import hashlib
import json

import structlog
from pydantic import JsonValue, ValidationError

from skriptoteket.application.curated_apps.reagent_prep_chef import (
    ReagentPrepChefRiskAssessmentDraft,
    ReagentPrepChefRiskAssessmentInputs,
    ReagentPrepChefRiskAssessmentRequest,
    ReagentPrepChefRiskAssessmentResult,
    ReagentPrepChefRiskExportGate,
    ReagentPrepChefRiskItem,
    ReagentPrepChefSdsSnapshot,
)
from skriptoteket.domain.curated_apps.models import curated_app_tool_id
from skriptoteket.domain.curated_apps.reagent_prep_chef.errors import (
    ReagentPrepChefErrorCode,
    rpc_validation_error,
)
from skriptoteket.domain.curated_apps.reagent_prep_chef.models import HazardEntry
from skriptoteket.domain.curated_apps.reagent_prep_chef.risk_assessment import (
    RiskTemplate,
    filter_templates_by_hazard_codes,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import User
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.reagent_prep_chef import (
    ReagentPrepChefHazardStoreProtocol,
    ReagentPrepChefPrepHandlerProtocol,
    ReagentPrepChefRiskAssessmentHandlerProtocol,
    ReagentPrepChefRiskTemplateStoreProtocol,
    ReagentPrepChefSdsStoreProtocol,
)
from skriptoteket.protocols.tool_sessions import ToolSessionRepositoryProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol

logger = structlog.get_logger(__name__)

APP_ID = "chemistry.reagent_prep_chef"
RISK_CONTEXT = "curated-app-risk-assessment:v1"
RISK_KEY = "risk_inputs"
PREP_FINGERPRINT_KEY = "prep_fingerprint"


def _parse_inputs(value: object) -> ReagentPrepChefRiskAssessmentInputs | None:
    if not isinstance(value, dict):
        return None
    try:
        return ReagentPrepChefRiskAssessmentInputs.model_validate(value)
    except ValidationError:
        return None


def _parse_prep_fingerprint(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized or None


def _prep_fingerprint(command: ReagentPrepChefRiskAssessmentRequest) -> str:
    payload = command.prep.model_dump(mode="json")
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _missing_context_fields(*, context: object) -> list[str]:
    if context is None:
        return ["scope", "participants", "approver", "assessment_date", "next_review_date"]

    missing = []
    scope = getattr(context, "scope", None)
    participants = getattr(context, "participants", None)
    approver = getattr(context, "approver", None)
    assessment_date = getattr(context, "assessment_date", None)
    next_review_date = getattr(context, "next_review_date", None)

    if not (scope or "").strip():
        missing.append("scope")
    if not (participants or "").strip():
        missing.append("participants")
    if not (approver or "").strip():
        missing.append("approver")
    if assessment_date is None:
        missing.append("assessment_date")
    if next_review_date is None:
        missing.append("next_review_date")
    return missing


def _apply_override(
    *,
    template: RiskTemplate,
    confirmed: bool,
    measures_override: list[str] | None,
    hazard_codes: list[str],
) -> ReagentPrepChefRiskItem:
    measures = measures_override if measures_override is not None else list(template.measures)
    return ReagentPrepChefRiskItem(
        id=template.id,
        title=template.title,
        description=template.description,
        hazard_codes=hazard_codes,
        measures=measures,
        confirmed=confirmed,
    )


def _build_templates(
    *,
    hazard_entry: HazardEntry,
    risk_templates: ReagentPrepChefRiskTemplateStoreProtocol,
) -> list[RiskTemplate]:
    templates = risk_templates.get()
    hazard_codes = set(hazard_entry.hazard_codes)
    hazard_specific = filter_templates_by_hazard_codes(
        templates=templates.hazard_risks,
        hazard_codes=hazard_codes,
    )
    combined: list[RiskTemplate] = list(templates.generic_risks) + hazard_specific

    deduped: list[RiskTemplate] = []
    seen: set[str] = set()
    for template in combined:
        if template.id in seen:
            continue
        seen.add(template.id)
        deduped.append(template)
    return deduped


class ReagentPrepChefRiskAssessmentHandler(ReagentPrepChefRiskAssessmentHandlerProtocol):
    def __init__(
        self,
        *,
        prep: ReagentPrepChefPrepHandlerProtocol,
        hazards: ReagentPrepChefHazardStoreProtocol,
        risk_templates: ReagentPrepChefRiskTemplateStoreProtocol,
        sds_store: ReagentPrepChefSdsStoreProtocol,
        sessions: ToolSessionRepositoryProtocol,
        uow: UnitOfWorkProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> None:
        self._prep = prep
        self._hazards = hazards
        self._risk_templates = risk_templates
        self._sds_store = sds_store
        self._sessions = sessions
        self._uow = uow
        self._id_generator = id_generator

    async def handle(
        self,
        *,
        actor: User,
        command: ReagentPrepChefRiskAssessmentRequest,
    ) -> ReagentPrepChefRiskAssessmentResult:
        prep_result = await self._prep.handle(actor=actor, command=command.prep)
        tool_id = curated_app_tool_id(app_id=APP_ID)
        current_fingerprint = _prep_fingerprint(command)

        async with self._uow:
            session = await self._sessions.get_or_create(
                session_id=self._id_generator.new_uuid(),
                tool_id=tool_id,
                user_id=actor.id,
                context=RISK_CONTEXT,
            )

            if command.reset or command.inputs is not None:
                next_state: dict[str, JsonValue] = {}
                if command.inputs is not None and not command.reset:
                    next_state[RISK_KEY] = command.inputs.model_dump(mode="json")
                    next_state[PREP_FINGERPRINT_KEY] = current_fingerprint

                session = await self._sessions.update_state(
                    tool_id=tool_id,
                    user_id=actor.id,
                    context=RISK_CONTEXT,
                    expected_state_rev=command.expected_state_rev,
                    state=next_state,
                )

        stored_inputs = _parse_inputs(session.state.get(RISK_KEY))
        stored_fingerprint = _parse_prep_fingerprint(session.state.get(PREP_FINGERPRINT_KEY))

        warnings: list[str] = []
        if stored_inputs is None and session.state.get(RISK_KEY):
            logger.warning(
                "Invalid reagent prep chef risk inputs; ignoring",
                actor_id=str(actor.id),
                context=RISK_CONTEXT,
            )

        if (
            stored_inputs is not None
            and stored_fingerprint
            and stored_fingerprint != current_fingerprint
        ):
            warnings.append("Riskutkastet gäller en annan beräkning och kan inte återställas.")
            stored_inputs = None

        inputs = None if command.reset else (command.inputs or stored_inputs)
        overrides = inputs.overrides if inputs else []
        overrides_by_id = {item.id: item for item in overrides}

        hazard_entry = self._hazards.lookup(formula_clean=prep_result.sheet.chemistry.formula_clean)
        if hazard_entry is None:
            raise rpc_validation_error(
                app_code=ReagentPrepChefErrorCode.RISK_CHEMICAL_MISSING,
                message="Okänt ämne: saknar säkerhetsdata i appen.",
                details={"formula": prep_result.sheet.chemistry.formula_clean},
            )

        sds_ref = hazard_entry.key
        markdown_available = False
        pdf_available = False
        provider = None
        revision = None
        try:
            entry = self._sds_store.get_entry(sds_ref=sds_ref)
            markdown_available = True
            pdf_available = True
            provider = entry.provider
            revision = entry.revision
        except DomainError as exc:
            if exc.code != ErrorCode.NOT_FOUND:
                raise
            warnings.append("SDS saknas offline för ämnet.")

        templates = _build_templates(hazard_entry=hazard_entry, risk_templates=self._risk_templates)
        hazard_codes_set = set(hazard_entry.hazard_codes)
        risks: list[ReagentPrepChefRiskItem] = []

        for template in templates:
            override = overrides_by_id.get(template.id)
            measures_override = override.measures if override else None
            confirmed = override.confirmed if override else False
            matched_codes = (
                sorted(hazard_codes_set.intersection(template.hazard_codes_any))
                if template.hazard_codes_any
                else []
            )
            risks.append(
                _apply_override(
                    template=template,
                    confirmed=confirmed,
                    measures_override=measures_override,
                    hazard_codes=matched_codes,
                )
            )

        missing_confirmations = [item.id for item in risks if not item.confirmed]
        requires_confirmation = len(missing_confirmations) > 0

        missing_context_fields = _missing_context_fields(context=inputs.context if inputs else None)
        export_gate = ReagentPrepChefRiskExportGate(
            ready=not requires_confirmation and not missing_context_fields,
            missing_confirmations=missing_confirmations,
            missing_context_fields=missing_context_fields,
        )

        sds_snapshot = ReagentPrepChefSdsSnapshot(
            sds_ref=sds_ref,
            markdown_available=markdown_available,
            pdf_available=pdf_available,
            provider=provider,
            revision=revision,
        )

        draft = ReagentPrepChefRiskAssessmentDraft(
            sheet=prep_result.sheet,
            sds=sds_snapshot,
            context=inputs.context if inputs else None,
            risks=risks,
            requires_confirmation=requires_confirmation,
            missing_confirmations=missing_confirmations,
            export_gate=export_gate,
        )

        return ReagentPrepChefRiskAssessmentResult(
            draft=draft,
            warnings=warnings,
            state_rev=session.state_rev,
        )
