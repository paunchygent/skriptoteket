"""Responses grouping pass: source references only (TASK-SKRIPT-39-05-04 step 1, Grouping A).

One low-effort ``gpt-6-luna`` call returns each question with its subparts and answer
key, each shared instruction or passage with its scope, single owner and governed
questions, the title and header anchors. Instructions and schema are Grouping A as
measured in the feasibility step (2026-10-11). A failed call or an unusable manifest is
retried; three failures stop the grouping.

Relationships:
    Implements ``protocols.exam_grouping.ExamGrouperProtocol`` over the leased
    ``DocxBuildRoundExchange``; ``domain.curated_apps.exam_workspace.docx_manifest``
    validates the output against the chunk anchors.
"""

from __future__ import annotations

import json
from uuid import UUID

from pydantic import JsonValue

from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_rounds import (
    DocxBuildRoundExchange,
    DocxBuildRoundFailure,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_llm_contracts import (
    StructuredLLMProviderProfile,
    StructuredLLMRequest,
    StructuredLLMUsage,
    StructuredOutputSpec,
    estimate_prompt_tokens,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.docx_manifest import (
    ManifestInvalid,
    manifest_from_output,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_model_source import marked_source_text
from skriptoteket.protocols.exam_grouping import (
    ExamGrouperProtocol,
    ExamGrouping,
    ExamGroupingError,
)

MAX_GROUPING_ATTEMPTS = 3

GROUPING_INSTRUCTIONS = (
    "You map the structure of an exam document given as ordered source chunks, each "
    "with an anchor.\n"
    "Return only anchor references. Never write question text, options or answers.\n"
    "\n"
    "Rules:\n"
    "- A question is one student task. Its anchors are its number or heading line, "
    "stem, options, tables, answer lines or blanks, and all its subparts.\n"
    "- A chunk of kind drawing is a picture with no text; the question it stands with "
    "lists it in its anchors.\n"
    "- Subparts (a), b), 1., 2. inside one task) stay inside their parent question. "
    "List them in the question's anchors and also in subpart_anchors.\n"
    "- One question carries at most one set of choices and one answer key. A "
    "numbered unit with its own choices and its own answer is a question of its own, "
    "also when one heading, instruction or points line stands above several such "
    "units. Such text governs all of them and joins none of them into one question: "
    "a heading or instruction above several questions is shared context with scope "
    'section_instruction and owner "exam", governing those questions. A heading or '
    "points line of ONE question is in that question's anchors and opens it. "
    "Part labels such as a), b) inside "
    "one question's body, which share one response and one answer, stay subparts of "
    "that question.\n"
    "- answer_key_anchors of a question: chunks that give its correct answer, sample "
    "answer or grading facit.\n"
    "- shared_contexts: a chunk with an instruction, passage, word bank or other "
    "context that governs several questions, including a section instruction before a"
    " run of questions. Give the question ids it governs, its scope, and exactly one "
    'owner: "exam" for section- or exam-level text, otherwise the id of the single '
    "question it belongs to. A shared chunk never also appears in a question's "
    "anchors.\n"
    "- title_anchors: the exam title.\n"
    "- header_anchors: lines whose whole content is metadata: the course name or a "
    'total. For example, "Poäng: 15 poäng" is header metadata; '
    '"Del 1: litteraturhistoria, 15 poäng" also carries heading words and is structure, '
    "not a header anchor. A heading opens its question, or is a section_instruction "
    "over several questions; its points are that question's or part's printed points. "
    "Each header entry gives its anchor, kind (course, exam_total or part_total), and "
    "governs. A part total lists the question ids of its part in governs; course and "
    "exam total give an empty governs.\n"
    "- Other metadata lines, such as name and date lines, are shared_contexts with "
    'scope exam_metadata and owner "exam". Course and totals go to header_anchors.\n'
    "- Every input anchor appears exactly once across questions[].anchors, "
    "questions[].answer_key_anchors, shared_contexts, title_anchors and "
    "header_anchors. subpart_anchors repeat anchors already in the question's anchors."
    "\n"
    "- Question ids are q1, q2, ... in source order.\n"
    "- Judge structure from layout, numbering and instructions, not from the subject "
    "matter."
)

GROUPING_SCHEMA: dict[str, JsonValue] = {
    "type": "object",
    "properties": {
        "title_anchors": {"type": "array", "items": {"type": "string"}},
        "questions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "anchors": {"type": "array", "items": {"type": "string"}},
                    "subpart_anchors": {"type": "array", "items": {"type": "string"}},
                    "answer_key_anchors": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["id", "anchors", "subpart_anchors", "answer_key_anchors"],
                "additionalProperties": False,
            },
        },
        "shared_contexts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "anchor": {"type": "string"},
                    "scope": {
                        "type": "string",
                        "enum": [
                            "section_instruction",
                            "shared_passage",
                            "word_bank",
                            "exam_metadata",
                            "other",
                        ],
                    },
                    "owner": {"type": "string"},
                    "governs": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["anchor", "scope", "owner", "governs"],
                "additionalProperties": False,
            },
        },
        "header_anchors": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "anchor": {"type": "string"},
                    "kind": {"type": "string", "enum": ["course", "exam_total", "part_total"]},
                    "governs": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["anchor", "kind", "governs"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["title_anchors", "questions", "shared_contexts", "header_anchors"],
    "additionalProperties": False,
}


def render_chunks(chunks: tuple[DocxChunk, ...]) -> str:
    return "\n".join(
        f"[{chunk.anchor}] ({chunk.kind}) {marked_source_text(chunk)}" for chunk in chunks
    )


def build_grouping_request(
    *,
    job_id: UUID,
    attempt: int,
    chunks: tuple[DocxChunk, ...],
    profile: StructuredLLMProviderProfile,
) -> StructuredLLMRequest:
    payload = render_chunks(chunks)
    return StructuredLLMRequest(
        job_id=str(job_id),
        item_id=f"docx_grouping_{attempt}",
        item_type="docx_exam_grouping",
        prompt_template_version="exam_source_manifest_v1",
        system_prompt=GROUPING_INSTRUCTIONS,
        user_payload=payload,
        output_spec=StructuredOutputSpec("exam_source_manifest", "1", GROUPING_SCHEMA),
        estimated_input_tokens=estimate_prompt_tokens(
            GROUPING_INSTRUCTIONS + payload + json.dumps(GROUPING_SCHEMA)
        ),
        max_output_tokens=profile.max_output_tokens,
    )


class ResponsesExamGrouper(ExamGrouperProtocol):
    """Group an exam's chunks with at most three leased Responses calls."""

    def __init__(
        self, *, exchange: DocxBuildRoundExchange, profile: StructuredLLMProviderProfile
    ) -> None:
        self._exchange = exchange
        self._profile = profile

    async def group(self, *, job_id: UUID, chunks: tuple[DocxChunk, ...]) -> ExamGrouping:
        usage: list[StructuredLLMUsage] = []
        failure = ExamGroupingError(
            "Provets struktur kunde inte läsas ut. Kontrollera källtexten manuellt.",
            code="grouping_failed",
        )
        for attempt in range(1, MAX_GROUPING_ATTEMPTS + 1):
            request = build_grouping_request(
                job_id=job_id, attempt=attempt, chunks=chunks, profile=self._profile
            )
            try:
                reply = await self._exchange.exchange(request, self._profile)
            except DocxBuildRoundFailure as error:
                if error.code in {"lease_refused", "text_budget_exceeded"}:
                    raise ExamGroupingError(
                        str(error), code=error.code, detail=error.detail
                    ) from error
                failure = ExamGroupingError(str(error), code=error.code, detail=error.detail)
                continue
            usage.append(reply.response.usage)
            if reply.response.finish_reason not in {None, "completed"}:
                failure = ExamGroupingError(
                    str(failure),
                    code="grouping_incomplete",
                    detail=str(reply.response.finish_reason),
                )
                continue
            try:
                manifest = manifest_from_output(reply.response.content, chunks)
            except ManifestInvalid as error:
                failure = ExamGroupingError(str(failure), code=error.code, detail=str(error))
                continue
            return ExamGrouping(manifest=manifest, usage=tuple(usage))
        raise failure
