"""Riskbedömning draft handler for the Reagent Prep Chef curated app.

Builds a deterministic, restorable risk assessment draft from:
- the computed prep sheet (via the prep handler),
- curated hazards + SDS-derived signals (CLP bands, density, heuristics),
- repo-owned risk templates and teacher overrides stored in tool_sessions.

PR-0062: draft generation is best-effort w.r.t. SDS completeness. Missing SDS-derived
inputs are surfaced via explicit `missing_flags` + server-driven `export_gate`, while
export remains strict/offline.
"""

from __future__ import annotations

import hashlib
import json

import structlog
from pydantic import JsonValue, ValidationError

from skriptoteket.application.curated_apps.reagent_prep_chef import (
    ReagentPrepChefChemistryHeuristics,
    ReagentPrepChefClpClassification,
    ReagentPrepChefRiskAssessmentDraft,
    ReagentPrepChefRiskAssessmentInputs,
    ReagentPrepChefRiskAssessmentRequest,
    ReagentPrepChefRiskAssessmentResult,
    ReagentPrepChefRiskExportGate,
    ReagentPrepChefRiskItem,
    ReagentPrepChefRiskMissingFlag,
    ReagentPrepChefRiskRating,
    ReagentPrepChefSdsSnapshot,
)
from skriptoteket.domain.curated_apps.models import curated_app_tool_id
from skriptoteket.domain.curated_apps.reagent_prep_chef.errors import (
    ReagentPrepChefErrorCode,
    rpc_validation_error,
)
from skriptoteket.domain.curated_apps.reagent_prep_chef.models import (
    ClpBand,
    HazardEntry,
    HazardSdsData,
)
from skriptoteket.domain.curated_apps.reagent_prep_chef.risk_assessment import (
    DEFAULT_RISK_LEVELS,
    RiskTemplate,
    RiskTemplates,
    filter_templates_by_hazard_codes,
    resolve_risk_level,
    score_risk,
    select_clp_band,
)
from skriptoteket.domain.identity.models import User
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.reagent_prep_chef import (
    ReagentPrepChefHazardStoreProtocol,
    ReagentPrepChefPrepHandlerProtocol,
    ReagentPrepChefRiskAssessmentHandlerProtocol,
    ReagentPrepChefRiskTemplateStoreProtocol,
    ReagentPrepChefSdsIndexStoreProtocol,
)
from skriptoteket.protocols.tool_sessions import ToolSessionRepositoryProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol

logger = structlog.get_logger(__name__)

APP_ID = "chemistry.reagent_prep_chef"
RISK_CONTEXT = "curated-app-risk-assessment:v1"
RISK_KEY = "risk_inputs"
PREP_FINGERPRINT_KEY = "prep_fingerprint"

MISSING_FLAGS_ORDER: list[ReagentPrepChefRiskMissingFlag] = [
    "sds_ref_missing",
    "sds_pdf_missing",
    "sds_density_missing",
    "sds_clp_bands_missing",
    "sds_heuristics_missing",
    "clp_unavailable_for_target",
    "heuristics_unavailable",
]

EXPORT_BLOCKING_FLAGS: set[ReagentPrepChefRiskMissingFlag] = {
    "sds_pdf_missing",
    "sds_density_missing",
    "sds_heuristics_missing",
    "heuristics_unavailable",
}


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


def _build_clp_classification(
    *,
    band: ClpBand | None,
    sds: HazardSdsData | None,
    fallback_notes: list[str],
) -> ReagentPrepChefClpClassification:
    if band is None:
        if sds is None:
            return ReagentPrepChefClpClassification()
        return ReagentPrepChefClpClassification(
            hazard_codes=list(sds.hazard_codes),
            pictograms=list(sds.pictograms),
            signal_word=sds.signal_word,
            notes=fallback_notes,
        )

    return ReagentPrepChefClpClassification(
        hazard_codes=list(band.hazard_codes),
        pictograms=list(band.pictograms),
        signal_word=band.signal_word,
        notes=list(band.notes),
    )


def _build_heuristics(*, hazard_entry: HazardEntry | None) -> ReagentPrepChefChemistryHeuristics:
    if hazard_entry is None:
        return ReagentPrepChefChemistryHeuristics()
    return ReagentPrepChefChemistryHeuristics(
        incompatibilities=list(hazard_entry.incompatibilities),
        exothermicity=hazard_entry.exothermicity,
        reaction_notes=list(hazard_entry.reaction_notes),
    )


def _build_rating(
    *, severity: int, likelihood: int, templates: RiskTemplates
) -> ReagentPrepChefRiskRating:
    levels = templates.risk_levels or DEFAULT_RISK_LEVELS
    score = score_risk(severity=severity, likelihood=likelihood)
    level = resolve_risk_level(score=score, levels=levels)
    return ReagentPrepChefRiskRating(
        severity=severity,
        likelihood=likelihood,
        score=score,
        level=level,
    )


def _apply_override(
    *,
    template: RiskTemplate,
    confirmed: bool,
    severity_override: int | None,
    likelihood_override: int | None,
    measures_override: list[str] | None,
    templates: RiskTemplates,
    hazard_codes: list[str],
) -> ReagentPrepChefRiskItem:
    computed = _build_rating(
        severity=template.default_severity,
        likelihood=template.default_likelihood,
        templates=templates,
    )
    severity = severity_override if severity_override is not None else template.default_severity
    likelihood = (
        likelihood_override if likelihood_override is not None else template.default_likelihood
    )
    final = _build_rating(severity=severity, likelihood=likelihood, templates=templates)

    measures = measures_override if measures_override is not None else list(template.measures)

    return ReagentPrepChefRiskItem(
        id=template.id,
        title=template.title,
        description=template.description,
        hazard_codes=hazard_codes,
        measures=measures,
        computed=computed,
        final=final,
        confirmed=confirmed,
    )


def _merge_sds(*, hazard: HazardEntry, sds: HazardSdsData) -> HazardEntry:
    return HazardEntry(
        key=hazard.key,
        display_name=hazard.display_name,
        hazard_codes=sds.hazard_codes,
        ppe=hazard.ppe,
        disposal=hazard.disposal,
        notes=hazard.notes,
        aliases=hazard.aliases,
        search_aliases=hazard.search_aliases,
        pubchem_cid=hazard.pubchem_cid,
        sds_ref=sds.sds_ref,
        clp_bands=sds.clp_bands,
        incompatibilities=sds.incompatibilities,
        exothermicity=sds.exothermicity,
        reaction_notes=sds.reaction_notes,
    )


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


def _has_heuristics(
    *,
    incompatibilities: tuple[str, ...],
    reaction_notes: tuple[str, ...],
    exothermicity: object,
) -> bool:
    return bool(incompatibilities) or bool(reaction_notes) or exothermicity is not None


def _ordered_missing_flags(
    missing_flags: set[ReagentPrepChefRiskMissingFlag],
) -> list[ReagentPrepChefRiskMissingFlag]:
    ordered = [flag for flag in MISSING_FLAGS_ORDER if flag in missing_flags]
    remaining = sorted(flag for flag in missing_flags if flag not in MISSING_FLAGS_ORDER)
    return [*ordered, *remaining]


class ReagentPrepChefRiskAssessmentHandler(ReagentPrepChefRiskAssessmentHandlerProtocol):
    def __init__(
        self,
        *,
        prep: ReagentPrepChefPrepHandlerProtocol,
        hazards: ReagentPrepChefHazardStoreProtocol,
        risk_templates: ReagentPrepChefRiskTemplateStoreProtocol,
        sds_index: ReagentPrepChefSdsIndexStoreProtocol,
        sessions: ToolSessionRepositoryProtocol,
        uow: UnitOfWorkProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> None:
        self._prep = prep
        self._hazards = hazards
        self._risk_templates = risk_templates
        self._sds_index = sds_index
        self._sessions = sessions
        self._uow = uow
        self._id_generator = id_generator

    async def handle(
        self,
        *,
        actor: User,
        command: ReagentPrepChefRiskAssessmentRequest,
        allow_fetch: bool = True,
        require_complete: bool = False,
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

        hazard_entry = self._hazards.lookup(formula_clean=prep_result.sheet.chemistry.formula_clean)
        sds_data: HazardSdsData | None = None

        if hazard_entry is None:
            raise rpc_validation_error(
                app_code=ReagentPrepChefErrorCode.RISK_CHEMICAL_MISSING,
                message="Okänt ämne: saknar kuraterad SDS-post.",
                details={"formula": prep_result.sheet.chemistry.formula_clean},
            )

        try:
            sds_data = await self._sds_index.ensure(
                hazard=hazard_entry,
                allow_fetch=allow_fetch,
                require_complete=require_complete,
            )
        except Exception as exc:  # noqa: BLE001
            if require_complete:
                raise rpc_validation_error(
                    app_code=ReagentPrepChefErrorCode.RISK_SDS_MISSING,
                    message="SDS saknas eller kunde inte laddas.",
                    details={"formula": hazard_entry.key},
                ) from exc
            warnings.append("SDS saknas: riskklassning kan inte beräknas. Öppna SDS.")
            sds_data = None

        if sds_data is not None:
            hazard_entry = _merge_sds(hazard=hazard_entry, sds=sds_data)

        band = None
        clp_fallback_notes: list[str] = []
        if hazard_entry.clp_bands:
            band = select_clp_band(
                bands=hazard_entry.clp_bands,
                molarity=command.prep.target_molarity,
            )
            if band is None:
                if require_complete:
                    raise rpc_validation_error(
                        app_code=ReagentPrepChefErrorCode.RISK_SDS_MISSING,
                        message="CLP-klassning saknas för vald koncentration.",
                        details={"formula": hazard_entry.key},
                    )
                if sds_data is not None:
                    warnings.append(
                        "SCL saknas för vald koncentration: CLP-koder visas som best effort."
                    )
                    clp_fallback_notes.append(
                        "SCL saknas för vald koncentration; visar SDS-koder (best effort)."
                    )
                else:
                    warnings.append("CLP-klassning kan inte beräknas för vald koncentration.")
        else:
            if require_complete:
                raise rpc_validation_error(
                    app_code=ReagentPrepChefErrorCode.RISK_SDS_MISSING,
                    message="CLP-klassning saknas i SDS.",
                    details={"formula": hazard_entry.key},
                )
            if sds_data is not None:
                warnings.append("SCL saknas i SDS: CLP-koder visas som best effort.")
                clp_fallback_notes.append("SCL saknas i SDS; visar SDS-koder (best effort).")

        clp = _build_clp_classification(
            band=band,
            sds=sds_data,
            fallback_notes=clp_fallback_notes,
        )
        heuristics = _build_heuristics(hazard_entry=hazard_entry)

        templates = self._risk_templates.get()
        overrides_by_id = {item.id: item for item in overrides}
        hazard_codes_set = set(clp.hazard_codes)
        hazard_templates = filter_templates_by_hazard_codes(
            templates=templates.hazard_risks,
            hazard_codes=hazard_codes_set,
        )

        combined_templates: list[RiskTemplate] = list(templates.generic_risks) + hazard_templates
        seen: set[str] = set()
        risks: list[ReagentPrepChefRiskItem] = []

        for template in combined_templates:
            if template.id in seen:
                continue
            seen.add(template.id)

            override = overrides_by_id.get(template.id)
            measures_override = override.measures if override else None
            severity_override = override.severity if override else None
            likelihood_override = override.likelihood if override else None
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
                    severity_override=severity_override,
                    likelihood_override=likelihood_override,
                    measures_override=measures_override,
                    templates=templates,
                    hazard_codes=matched_codes,
                )
            )

        missing_confirmations = [item.id for item in risks if not item.confirmed]
        requires_confirmation = len(missing_confirmations) > 0

        missing_flags: set[ReagentPrepChefRiskMissingFlag] = set()
        if sds_data is None:
            missing_flags.add("sds_pdf_missing")
        else:
            if sds_data.density_g_ml is None:
                missing_flags.add("sds_density_missing")
            if not sds_data.clp_bands:
                missing_flags.add("sds_clp_bands_missing")
            if not _has_heuristics(
                incompatibilities=sds_data.incompatibilities,
                reaction_notes=sds_data.reaction_notes,
                exothermicity=sds_data.exothermicity,
            ):
                missing_flags.add("sds_heuristics_missing")

        if hazard_entry.clp_bands and band is None:
            missing_flags.add("clp_unavailable_for_target")
        if not _has_heuristics(
            incompatibilities=hazard_entry.incompatibilities,
            reaction_notes=hazard_entry.reaction_notes,
            exothermicity=hazard_entry.exothermicity,
        ):
            missing_flags.add("heuristics_unavailable")

        ordered_missing_flags = _ordered_missing_flags(missing_flags)
        missing_context_fields = _missing_context_fields(context=inputs.context if inputs else None)
        missing_data_flags = [
            flag for flag in ordered_missing_flags if flag in EXPORT_BLOCKING_FLAGS
        ]
        export_gate = ReagentPrepChefRiskExportGate(
            ready=not requires_confirmation
            and not missing_context_fields
            and not missing_data_flags,
            missing_confirmations=missing_confirmations,
            missing_context_fields=missing_context_fields,
            missing_data_flags=missing_data_flags,
        )

        sds_snapshot = ReagentPrepChefSdsSnapshot(
            sds_ref=sds_data.sds_ref if sds_data is not None else None,
            pdf_available=sds_data is not None,
            missing_flags=[flag for flag in ordered_missing_flags if flag.startswith("sds_")],
            sources=list(sds_data.sources) if sds_data is not None else [],
        )

        draft = ReagentPrepChefRiskAssessmentDraft(
            sheet=prep_result.sheet,
            sds=sds_snapshot,
            context=inputs.context if inputs else None,
            clp=clp,
            heuristics=heuristics,
            risks=risks,
            requires_confirmation=requires_confirmation,
            missing_confirmations=missing_confirmations,
            missing_flags=ordered_missing_flags,
            export_gate=export_gate,
        )

        return ReagentPrepChefRiskAssessmentResult(
            draft=draft,
            warnings=warnings,
            state_rev=session.state_rev,
        )
