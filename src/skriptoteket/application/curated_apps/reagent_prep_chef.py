from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from skriptoteket.application.scripting.vault import VaultFileInfo

type SourceType = Literal["solid", "liquid_stock"]
type SafetyLevel = Literal["curated", "unknown"]


class ReagentPrepChefPrepRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    chemical_formula: str
    target_molarity: Decimal
    vol_per_group_ml: Decimal
    student_count: int
    students_per_group: int = 2
    safety_factor: Decimal = Decimal("0.10")
    source_type: SourceType = "solid"
    stock_molarity: Decimal | None = None
    solute_purity: Decimal = Decimal("1.0")

    @field_validator("chemical_formula")
    @classmethod
    def _strip_formula(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Ange en kemisk formel.")
        return normalized

    @field_validator("target_molarity")
    @classmethod
    def _validate_target_molarity(cls, value: Decimal) -> Decimal:
        if value <= 0:
            raise ValueError("Målmolaritet måste vara större än 0.")
        return value

    @field_validator("vol_per_group_ml")
    @classmethod
    def _validate_volume(cls, value: Decimal) -> Decimal:
        if value <= 0:
            raise ValueError("Volym per grupp måste vara större än 0 mL.")
        return value

    @field_validator("student_count")
    @classmethod
    def _validate_student_count(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("Antal elever måste vara större än 0.")
        return value

    @field_validator("students_per_group")
    @classmethod
    def _validate_students_per_group(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("Elever per grupp måste vara större än 0.")
        return value

    @field_validator("safety_factor")
    @classmethod
    def _validate_safety_factor(cls, value: Decimal) -> Decimal:
        if value < 0 or value > Decimal("0.50"):
            raise ValueError("Marginal måste vara mellan 0 och 0,5.")
        return value

    @field_validator("solute_purity")
    @classmethod
    def _validate_solute_purity(cls, value: Decimal) -> Decimal:
        if value <= 0 or value > 1:
            raise ValueError("Renhet måste vara > 0 och ≤ 1.")
        return value


class ReagentPrepChefMeta(BaseModel):
    model_config = ConfigDict(frozen=True)

    generated_at: datetime
    app_version: str


class ReagentPrepChefLogistics(BaseModel):
    model_config = ConfigDict(frozen=True)

    total_groups: int
    total_volume_ml: str
    base_total_volume_ml: str
    safety_factor_pct: str


class ReagentPrepChefSafety(BaseModel):
    model_config = ConfigDict(frozen=True)

    level: SafetyLevel
    message: str | None = None
    display_name: str | None = None
    hazard_codes: list[str] = Field(default_factory=list)
    ppe: list[str] = Field(default_factory=list)
    disposal: str | None = None
    notes: list[str] = Field(default_factory=list)


class ReagentPrepChefChemistry(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_type: SourceType
    formula_clean: str
    molar_mass_g_mol: str
    moles_required: str

    target_molarity: str
    solute_purity: str
    stock_molarity: str | None = None

    mass_g: str | None = None
    stock_volume_ml: str | None = None
    diluent_volume_ml: str | None = None


class ReagentPrepChefPrepSheet(BaseModel):
    model_config = ConfigDict(frozen=True)

    meta: ReagentPrepChefMeta
    logistics: ReagentPrepChefLogistics
    chemistry: ReagentPrepChefChemistry
    instructions: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    safety: ReagentPrepChefSafety


class ReagentPrepChefPrepResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    sheet: ReagentPrepChefPrepSheet


class ReagentPrepChefChemicalOption(BaseModel):
    model_config = ConfigDict(frozen=True)

    key: str
    display_name: str
    aliases: list[str] = Field(default_factory=list)


class ReagentPrepChefChemicalsResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    chemicals: list[ReagentPrepChefChemicalOption] = Field(default_factory=list)


class ReagentPrepChefDefaultsResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    defaults: ReagentPrepChefPrepRequest | None = None
    state_rev: int


class ReagentPrepChefUpdateDefaultsRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    expected_state_rev: int = Field(..., ge=0)
    defaults: ReagentPrepChefPrepRequest | None = None


class ReagentPrepChefSavePdfRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    prep: ReagentPrepChefPrepRequest
    name: str | None = None


class ReagentPrepChefSavePdfResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    file: VaultFileInfo


class ReagentPrepChefSaveDefaultsRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    defaults: ReagentPrepChefPrepRequest
    name: str | None = None


class ReagentPrepChefSaveDefaultsResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    file: VaultFileInfo


class ReagentPrepChefLoadDefaultsRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    expected_state_rev: int = Field(..., ge=0)
    file_id: UUID


class ReagentPrepChefRiskContext(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    scope: str | None = None
    location: str | None = None
    participants: str | None = None
    approver: str | None = None
    assessment_date: date | None = None
    next_review_date: date | None = None
    local_routines: str | None = None


class ReagentPrepChefRiskItemOverride(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    severity: int | None = Field(default=None, ge=1, le=5)
    likelihood: int | None = Field(default=None, ge=1, le=5)
    measures: list[str] | None = None
    confirmed: bool = False


class ReagentPrepChefRiskAssessmentInputs(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    context: ReagentPrepChefRiskContext | None = None
    overrides: list[ReagentPrepChefRiskItemOverride] = Field(default_factory=list)


class ReagentPrepChefRiskAssessmentRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    prep: ReagentPrepChefPrepRequest
    expected_state_rev: int = Field(0, ge=0)
    inputs: ReagentPrepChefRiskAssessmentInputs | None = None
    reset: bool = False


RiskLevel = Literal["low", "medium", "high", "critical"]


class ReagentPrepChefRiskRating(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    severity: int = Field(ge=1, le=5)
    likelihood: int = Field(ge=1, le=5)
    score: int = Field(ge=1, le=25)
    level: RiskLevel


class ReagentPrepChefClpClassification(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    hazard_codes: list[str] = Field(default_factory=list)
    pictograms: list[str] = Field(default_factory=list)
    signal_word: Literal["danger", "warning"] | None = None
    notes: list[str] = Field(default_factory=list)


class ReagentPrepChefChemistryHeuristics(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    incompatibilities: list[str] = Field(default_factory=list)
    exothermicity: Literal["none", "low", "medium", "high"] | None = None
    reaction_notes: list[str] = Field(default_factory=list)


class ReagentPrepChefRiskItem(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    title: str
    description: str | None = None
    hazard_codes: list[str] = Field(default_factory=list)
    measures: list[str] = Field(default_factory=list)
    computed: ReagentPrepChefRiskRating
    final: ReagentPrepChefRiskRating
    confirmed: bool


class ReagentPrepChefRiskAssessmentDraft(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    sheet: ReagentPrepChefPrepSheet
    sds_ref: str | None = None
    context: ReagentPrepChefRiskContext | None = None
    clp: ReagentPrepChefClpClassification
    heuristics: ReagentPrepChefChemistryHeuristics
    risks: list[ReagentPrepChefRiskItem]
    requires_confirmation: bool
    missing_confirmations: list[str] = Field(default_factory=list)


class ReagentPrepChefRiskAssessmentResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    draft: ReagentPrepChefRiskAssessmentDraft
    warnings: list[str] = Field(default_factory=list)
    state_rev: int
