"""Exam.net-oriented QTI package contracts.

Purpose:
    Define the reusable value objects for QTI 2.1 package generation,
    validation reporting, proof-gated Exam.net support, and manual follow-up.

Relationships:
    - Consumed by QTI XML, package planning, validation, sample, and DigiExam
      adapter modules.
    - Shared by future DigiExam migration and Exam.net authoring bundle
      implementations before any service route materializes artifacts.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Literal, TypeAlias

EXAMNET_QTI_VERSION: Literal["2.1"] = "2.1"
EXAMNET_QTI_PACKAGE_SCHEMA_VERSION: Literal["examnet_qti_package_plan_v1"] = (
    "examnet_qti_package_plan_v1"
)
EXAMNET_QTI_VALIDATION_REPORT_SCHEMA_VERSION: Literal["examnet_qti_validation_report_v1"] = (
    "examnet_qti_validation_report_v1"
)
EXAMNET_QTI_GENERATOR_VERSION: Literal["examnet_qti_2_1_v1"] = "examnet_qti_2_1_v1"
EXAMNET_QTI_AUTOMATIC_PROFILE_ID: Literal["examnet_qti_2_1_v1"] = "examnet_qti_2_1_v1"
EXAMNET_QTI_MANUAL_UNKEYED_PROFILE_ID: Literal["unkeyed_manual_qti_2_1_v1"] = (
    "unkeyed_manual_qti_2_1_v1"
)
EXAMNET_QTI_PACKAGE_CONTENT_TYPE: Literal["application/zip"] = "application/zip"
EXAMNET_QTI_REPORT_CONTENT_TYPE: Literal["application/json"] = "application/json"


class ExamNetQtiInteractionType(StrEnum):
    """QTI interactions currently governed for the Exam.net target profile."""

    SINGLE_CHOICE = "single_choice"
    MULTIPLE_RESPONSE = "multiple_response"
    GAP_FILL = "gap_fill"
    FREE_TEXT = "free_text"
    MATCHING = "matching"


class ExamNetQtiEvaluationMode(StrEnum):
    """Whether the converter asserts automatic evaluation for the QTI item."""

    AUTOMATIC = "automatic_evaluation"
    MANUAL_UNKEYED = "manual_unkeyed"


class ExamNetQtiManualRepresentation(StrEnum):
    """Manual/unkeyed preservation shape selected for a QTI item."""

    NATIVE_INTERACTION = "native_interaction"
    FREE_TEXT_PRESERVATION = "free_text_preservation"


class ExamNetQtiPackageStatus(StrEnum):
    """Top-level package generation status."""

    PASSED = "passed"
    BLOCKED = "blocked"
    FAILED = "failed"


class ExamNetQtiValidationStatus(StrEnum):
    """Validation-layer status values emitted in validation reports."""

    PASSED = "passed"
    BLOCKED = "blocked"
    FAILED = "failed"
    NOT_RUN = "not_run"
    EXTERNAL_VALIDATOR_UNAVAILABLE = "external_validator_unavailable"


class ExamNetQtiExamNetProofStatus(StrEnum):
    """Exam.net import proof status for the generated package."""

    VENDOR_REPORTED_UNPROVEN = "vendor_reported_unproven"
    NOT_PROVEN = "not_proven"
    IMPORT_PROVEN = "import_proven"


class ExamNetQtiTargetSupportStatus(StrEnum):
    """Exam.net target-support boundary for the generated package."""

    VENDOR_REPORTED_MINIMUM = "vendor_reported_minimum"
    PROOF_GATED = "proof_gated"
    NOT_SUPPORTED_BY_EXAMNET = "not_supported_by_examnet"


class ExamNetQtiManualFollowUpReason(StrEnum):
    """Manual follow-up reasons owned by the QTI target profile."""

    MANUAL_ANSWER_KEY_REQUIRED = "manual_answer_key_required"
    AUTOMATIC_EVALUATION_UNSUPPORTED = "automatic_evaluation_unsupported"
    NOT_SUPPORTED_BY_EXAMNET = "not_supported_by_examnet"
    UNSUPPORTED_EXAMNET_QTI_RESOURCE = "unsupported_examnet_qti_resource"
    QTI_VALIDATION_FAILED = "qti_validation_failed"


@dataclass(frozen=True)
class ExamNetQtiChoice:
    """One visible choice in a QTI choice interaction."""

    identifier: str
    text: str


@dataclass(frozen=True)
class ExamNetQtiMatchEntry:
    """One visible entry of a QTI match interaction list, in the source's own order."""

    identifier: str
    text: str


@dataclass(frozen=True)
class ExamNetQtiMatchPair:
    """One exact left/right pair, carried only by the response and scoring data."""

    left_identifier: str
    left_text: str
    right_identifier: str
    right_text: str


@dataclass(frozen=True)
class ExamNetQtiTextEntryGap:
    """One keyed text-entry gap in a QTI gap-fill item."""

    response_identifier: str
    label: str
    accepted_values: tuple[str, ...]


@dataclass(frozen=True)
class ExamNetQtiImageResource:
    """One renderer-neutral image resource that may be carried in QTI."""

    asset_id: str
    filename: str
    media_type: str
    payload: bytes
    alt_text: str
    source_reference: str


@dataclass(frozen=True)
class ExamNetQtiUnsupportedResource:
    """One source resource omitted from the Exam.net QTI package."""

    resource_id: str
    resource_type: str
    label: str


@dataclass(frozen=True)
class ExamNetQtiPromptText:
    """One literal text run at its place inside a rich prompt paragraph."""

    text: str


@dataclass(frozen=True)
class ExamNetQtiPromptImage:
    """One image at its place; ``image_index`` addresses the item's image resources."""

    image_index: int


@dataclass(frozen=True)
class ExamNetQtiPromptGap:
    """One text-entry gap at its place; ``gap_index`` addresses the item's text-entry gaps."""

    gap_index: int


ExamNetQtiPromptSegment: TypeAlias = (
    ExamNetQtiPromptText | ExamNetQtiPromptImage | ExamNetQtiPromptGap
)


@dataclass(frozen=True)
class ExamNetQtiItem:
    """One QTI item request in the Exam.net target profile.

    A parent item carries ``children`` (items of any mix of interaction types, in
    order) and the ``instruction_lines`` they share; it exports as one assessment
    item holding one interaction per child, each with its own response, and every
    reader takes each child's own ``interaction_type``. Its ``image_resources`` are the children's
    in order, so package planning writes every image once under the parent.

    ``prompt_paragraphs`` carries the exact rich placement of text, images, and
    gaps; its image and gap indexes address this item's own ``image_resources``
    and ``text_entry_gaps`` in order. An empty value keeps the positionless
    ``prompt_lines`` rendering with appended images.
    """

    item_id: str
    sequence: int
    title: str
    interaction_type: ExamNetQtiInteractionType
    prompt_lines: tuple[str, ...]
    max_score: int | float | None
    prompt_paragraphs: tuple[tuple[ExamNetQtiPromptSegment, ...], ...] = ()
    evaluation_mode: ExamNetQtiEvaluationMode = ExamNetQtiEvaluationMode.AUTOMATIC
    manual_representation: ExamNetQtiManualRepresentation = (
        ExamNetQtiManualRepresentation.NATIVE_INTERACTION
    )
    source_item_type: str | None = None
    free_text_criterion_points: int | float | None = None
    choices: tuple[ExamNetQtiChoice, ...] = ()
    correct_choice_identifiers: tuple[str, ...] = ()
    text_entry_gaps: tuple[ExamNetQtiTextEntryGap, ...] = ()
    match_pairs: tuple[ExamNetQtiMatchPair, ...] = ()
    match_left: tuple[ExamNetQtiMatchEntry, ...] = ()
    match_right: tuple[ExamNetQtiMatchEntry, ...] = ()
    image_resources: tuple[ExamNetQtiImageResource, ...] = ()
    unsupported_resources: tuple[ExamNetQtiUnsupportedResource, ...] = ()
    instruction_lines: tuple[str, ...] = ()
    children: tuple[ExamNetQtiItem, ...] = ()


@dataclass(frozen=True)
class ExamNetQtiManualFollowUp:
    """One teacher-facing manual action emitted by QTI generation."""

    item_id: str
    sequence: int
    title: str
    reason_code: ExamNetQtiManualFollowUpReason
    message: str
    affected_targets: tuple[str, ...]


@dataclass(frozen=True)
class ExamNetQtiPackageFile:
    """One deterministic file planned for a QTI zip package."""

    relative_path: str
    content_type: str
    payload: bytes
    sha256: str


@dataclass(frozen=True)
class ExamNetQtiPackagePlan:
    """Filesystem-free QTI package plan."""

    schema_version: Literal["examnet_qti_package_plan_v1"]
    generator_version: Literal["examnet_qti_2_1_v1"]
    qti_version: Literal["2.1"]
    profile_id: Literal["examnet_qti_2_1_v1", "unkeyed_manual_qti_2_1_v1"]
    package_name: str
    status: ExamNetQtiPackageStatus
    target_support_status: ExamNetQtiTargetSupportStatus
    examnet_proof_status: ExamNetQtiExamNetProofStatus
    items: tuple[ExamNetQtiItem, ...]
    files: tuple[ExamNetQtiPackageFile, ...]
    manual_follow_ups: tuple[ExamNetQtiManualFollowUp, ...]
    warnings: tuple[str, ...]


@dataclass(frozen=True)
class ExamNetQtiValidatorResult:
    """One validation-layer result for the report artifact."""

    name: str
    version: str
    layer: str
    status: ExamNetQtiValidationStatus
    message: str


@dataclass(frozen=True)
class ExamNetQtiValidationReport:
    """JSON-serializable QTI validation report contract."""

    schema_version: Literal["examnet_qti_validation_report_v1"]
    generator_version: Literal["examnet_qti_2_1_v1"]
    qti_version: Literal["2.1"]
    profile_id: Literal["examnet_qti_2_1_v1", "unkeyed_manual_qti_2_1_v1"]
    package_filename: str
    package_sha256: str | None
    package_status: ExamNetQtiPackageStatus
    target_support_status: ExamNetQtiTargetSupportStatus
    examnet_proof_status: ExamNetQtiExamNetProofStatus
    validator_results: tuple[ExamNetQtiValidatorResult, ...]
    manual_follow_ups: tuple[ExamNetQtiManualFollowUp, ...]
    warnings: tuple[str, ...]
    errors: tuple[str, ...]
