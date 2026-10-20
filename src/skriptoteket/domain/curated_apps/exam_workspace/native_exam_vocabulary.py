"""The native exam document's closed vocabularies and identifier formats.

Purpose:
    Hold the StrEnum vocabularies and the identifier patterns the document model and the
    stored retry-source records share, so both import one vocabulary instead of each other.
    ``native_exam_document`` re-exports every name here.

Relationships:
    Imported by ``native_exam_document`` and ``native_exam_retry_records``; neither imports
    back, so this stays a leaf module.
"""

from __future__ import annotations

from enum import StrEnum

ITEM_ID_PATTERN = r"^item_[0-9]{3,4}$"
CHOICE_ID_PATTERN = r"^choice_[0-9]{3}$"
GAP_ID_PATTERN = r"^gap_[0-9]{3}$"
MATCH_LEFT_ID_PATTERN = r"^left_[0-9]{3}$"
MATCH_RIGHT_ID_PATTERN = r"^right_[0-9]{3}$"
ASSET_ID_PATTERN = r"^asset_[0-9a-f]{16}$"
SHA256_PATTERN = r"^[0-9a-f]{64}$"


class NativeExamItemKind(StrEnum):
    """Writer-proven item subset (EPIC-SKRIPT-39 E3)."""

    FREE_TEXT = "free_text"
    SINGLE_CHOICE = "single_choice"
    MULTIPLE_RESPONSE = "multiple_response"
    GAP_FILL = "gap_fill"
    INLINE_CHOICE = "inline_choice"
    MATCHING = "matching"
    ORDERING = "ordering"


IMPORTABLE_ITEM_KINDS = frozenset(NativeExamItemKind) - {NativeExamItemKind.ORDERING}
"""The kinds an import or a retry may produce; teachers author ordering only (39-06-08 D3)."""


class NativeParseOrigin(StrEnum):
    SOURCE_FALLBACK = "source_fallback"
    DETERMINISTIC = "deterministic"
    LLM_PARSED = "llm_parsed"
    TEACHER_CREATED = "teacher_created"
    # The teacher chose the type of a question the import printed from source.
    TEACHER_RETYPED = "teacher_retyped"


class NativeItemReviewState(StrEnum):
    REVIEW_REQUIRED = "review_required"
    REVIEW_COMPLETE = "review_complete"


class NativeAnswerKeyOrigin(StrEnum):
    """Provenance vocabulary aligned with the exam-conversion review states."""

    ABSENT = "absent"
    NOT_APPLICABLE = "not_applicable"
    SOURCE_PROVIDED = "source_provided"
    AI_INTERPRETED = "ai_interpreted"
    TEACHER_AUTHORED = "teacher_authored"
    MACHINE_PROPOSED = "machine_proposed"
    REVIEWED_ADVISORY = "reviewed_advisory"
