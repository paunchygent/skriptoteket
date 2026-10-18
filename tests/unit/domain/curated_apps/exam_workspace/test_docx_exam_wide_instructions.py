"""Exam-wide text belongs to the document's instructions once; metadata lines go nowhere.

The grouping's anchors decide it, never how a build reply bundles them: exam-wide chunks are
no batch's claims, so a reply can only read them as context, and assembly shows each one from
its own source. A printed total the points plan classifies as metadata is never instruction
text, even when a reply lists it as one.
"""

import json
from collections.abc import Mapping
from types import MappingProxyType
from uuid import UUID

import pytest
from pydantic import JsonValue

from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_assembly import (
    exam_metadata_anchors,
    exam_wide_anchors,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_admission import (
    admit_batch,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_rounds import (
    build_batch_request,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_state import (
    DocxBuildState,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_pipeline_batches import (
    batch_state,
    source_parts,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_run import (
    DocxConversionJob,
    DocxConversionRun,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_llm_contracts import (
    StructuredLLMEndpointKind,
    StructuredLLMProviderProfile,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import DocxBuildResult
from skriptoteket.domain.curated_apps.exam_workspace.docx_batches import (
    ConversionBatch,
    QuestionFamily,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.docx_manifest import SharedContext
from skriptoteket.domain.curated_apps.exam_workspace.docx_points_lines import printed_points_plan
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeExamItemKind,
)

pytestmark = pytest.mark.unit

_TOTAL = "Totalt: 70 poäng"
_BOX = "Instruktioner: Skriv tydligt."
_NAME = "Namn: ______"
_CHECK = "Kontrollera dina svar."
_DEL = "DEL A"
_Q1 = "1. Förklara vad ett substantiv är. (35 p)"
_Q2 = "2. Förklara vad ett verb är. (35 p)"
_TEXTS = {
    "body:0000": _TOTAL,
    "body:0001": _BOX,
    "body:0002": _NAME,
    "body:0003": _CHECK,
    "body:0004": _DEL,
    "body:0005": _Q1,
    "body:0006": _Q2,
}
_EXAM_WIDE = ("body:0001", "body:0003")
_METADATA = "body:0002"
_FREE_TEXT = frozenset({NativeExamItemKind.FREE_TEXT})


_UNGOVERNED: Mapping[str, frozenset[str]] = MappingProxyType({})
_DEL_GOVERNS_BOTH: Mapping[str, frozenset[str]] = MappingProxyType(
    {"body:0004": frozenset({"body:0005", "body:0006"})}
)


def _run(
    del_kind: str, *, exam_wide_total: bool = False, headings: frozenset[str] = frozenset()
) -> DocxConversionRun:
    """``headings`` holds the anchors other than the DEL line that are Word headings."""
    chunks = tuple(
        DocxChunk(
            anchor,
            del_kind if anchor == "body:0004" else "heading" if anchor in headings else "paragraph",
            text,
            text,
        )
        for anchor, text in _TEXTS.items()
    )
    job = DocxConversionJob(
        job_id=UUID(int=1),
        worker_id="worker",
        document_id=UUID(int=2),
        filename="prov.docx",
        source_sha256="0" * 64,
        source_docx=b"",
        chunks=chunks,
        course_key=None,
    )
    run = DocxConversionRun(job, 0.0)
    total = (SharedContext("body:0000", "other", "exam", ("q1", "q2")),) if exam_wide_total else ()
    run.contexts = (
        *total,
        SharedContext("body:0001", "other", "exam", ("q1", "q2")),
        SharedContext(_METADATA, "exam_metadata", "exam", ()),
        SharedContext("body:0003", "other", "exam", ("q1", "q2")),
    )
    run.context_anchors = frozenset(context.anchor for context in run.contexts)
    # The first question owns the exam-level lines before it; the second reads the shared ones.
    run.families = (
        QuestionFamily(
            question_id="q1",
            position=0,
            question_anchors=("body:0005",),
            claims=frozenset({"body:0000", "body:0001", _METADATA, "body:0003", "body:0004"})
            | {"body:0005"},
            reads=frozenset(),
        ),
        QuestionFamily(
            question_id="q2",
            position=1,
            question_anchors=("body:0006",),
            claims=frozenset({"body:0006"}),
            reads=frozenset(_EXAM_WIDE),
        ),
    )
    run.kinds = {"q1": NativeExamItemKind.FREE_TEXT, "q2": NativeExamItemKind.FREE_TEXT}
    return run


def _batch(run: DocxConversionRun) -> ConversionBatch:
    claims = frozenset().union(*(f.claims for f in run.families))
    return ConversionBatch(
        batch_id="w1-01",
        kinds=_FREE_TEXT,
        question_ids=("q1", "q2"),
        claims=claims,
        reads=frozenset().union(*(f.reads for f in run.families)) - claims,
    )


def _item(anchor: str, text: str) -> dict[str, JsonValue]:
    return {
        "source_anchors": [anchor],
        "outcome": "converted",
        "conflict_kind": None,
        "review_reason": None,
        "kind": "free_text",
        "key_source": None,
        "facit_text": None,
        "printed_label": anchor[-1],
        "body": [{"segments": [{"kind": "text", "text": text, "accepted_values": []}]}],
        "points": 35,
        "choices": [],
        "match_left": [],
        "match_right": [],
        "match_pairs": [],
        "criteria": [],
    }


def _instruction(*anchors: str) -> dict[str, JsonValue]:
    return {"text": "\n".join(_TEXTS[a] for a in anchors), "source_anchors": list(anchors)}


def _build(
    del_kind: str,
    instructions: tuple[tuple[str, ...], ...],
    *,
    exam_wide_total: bool = False,
    headings: frozenset[str] = frozenset(),
    governed: Mapping[str, frozenset[str]] = _UNGOVERNED,
) -> tuple[DocxBuildResult, DocxBuildState]:
    run = _run(del_kind, exam_wide_total=exam_wide_total, headings=headings)
    state = batch_state(run, _batch(run))
    admit_batch(
        {
            "items": [_item("body:0005", _Q1), _item("body:0006", _Q2)],
            "answer_key_anchors": [],
            "title": None,
            "instructions": [_instruction(*anchors) for anchors in instructions],
        },
        state,
    )
    questions = tuple(f.question_anchors for f in run.families)
    result = state.result(
        governed=governed,
        questions=questions,
        exam_wide=exam_wide_anchors(run.contexts, run.families),
        exam_metadata=exam_metadata_anchors(run.contexts),
    )
    return result, state


def _lines(paragraphs) -> list[str]:
    return [
        "".join(getattr(segment, "text", "") for segment in paragraph.segments)
        for paragraph in paragraphs
    ]


def _shown(result: DocxBuildResult) -> list[str]:
    document = result.document
    return [
        *_lines(document.instructions),
        *(line for item in document.items for line in item.plain_text_lines()),
        *(line for parent in document.parents for line in _lines(parent.instruction)),
    ]


_MIXED_BOX_NAME = (("body:0001", _METADATA), ("body:0004",))
_MIXED_BOX_NAME_DEL = (("body:0001", _METADATA, "body:0004"),)


@pytest.mark.parametrize("del_kind", ["paragraph", "heading"])
@pytest.mark.parametrize(
    "instructions",
    [
        _MIXED_BOX_NAME,
        _MIXED_BOX_NAME_DEL,
        (("body:0001",), (_METADATA,), ("body:0004",)),
        (("body:0004",),),
    ],
    ids=["box_and_name", "box_name_and_del", "each_alone", "only_del"],
)
def test_exam_wide_text_lands_in_document_instructions_once(del_kind, instructions):
    result, _ = _build(del_kind, instructions)
    document = result.document

    assert _lines(document.instructions) == [_BOX, _CHECK]
    assert not [line for line in _shown(result) if line.startswith("Namn")]
    for item in document.items:
        assert not set(item.plain_text_lines()) & {_BOX, _NAME, _CHECK}


@pytest.mark.parametrize("del_kind", ["paragraph", "heading"])
@pytest.mark.parametrize(
    "instructions",
    [_MIXED_BOX_NAME, _MIXED_BOX_NAME_DEL],
    ids=["box_name_separate", "box_name_in_del"],
)
def test_the_del_parent_holds_only_its_own_text(del_kind, instructions):
    document = _build(del_kind, instructions)[0].document

    assert len(document.items) == 2
    assert len(document.parents) == 1
    assert _lines(document.parents[0].instruction) == [_DEL]


def test_exam_wide_anchors_are_no_claims_of_the_batch_and_only_its_context():
    run = _run("heading")
    (part,) = source_parts(run, _batch(run))
    state = batch_state(run, part.batch)
    exam_wide = {*_EXAM_WIDE, _METADATA}

    assert not exam_wide & state.owned
    assert not exam_wide & {chunk.anchor for chunk in state.pending}
    assert exam_wide <= state.context_anchors
    assert exam_wide <= part.batch.reads
    assert not exam_wide & part.batch.claims
    request = build_batch_request(
        job_id=run.job.job_id,
        request_id="docx_w1-01",
        pending=state.pending,
        context=tuple(c for c in state.chunks if c.anchor in part.batch.reads),
        questions=state.questions,
        kinds=_FREE_TEXT,
        profile=StructuredLLMProviderProfile(
            provider_id="test",
            model="test",
            endpoint_kind=StructuredLLMEndpointKind.RESPONSES,
            is_remote=False,
            context_window_tokens=200_000,
            max_output_tokens=4_096,
        ),
    )
    schema = request.output_spec.json_schema
    definitions = _object(schema["$defs"])
    enums = [
        _path(schema, "properties", "answer_key_anchors", "items", "enum"),
        *(
            _path(definitions, name, "properties", "source_anchors", "items", "enum")
            for name in ("ProducedItem", "ProducedMetadata")
        ),
    ]
    for anchors in (_array(enum) for enum in enums):
        assert "body:0005" in anchors
        assert not exam_wide & {a for a in anchors if isinstance(a, str)}
    payload = _object(json.loads(request.user_payload))
    context = {_object(chunk)["anchor"] for chunk in _array(payload["context_chunks"])}
    assert exam_wide <= context


def _object(value: JsonValue) -> dict[str, JsonValue]:
    assert isinstance(value, dict)
    return value


def _array(value: JsonValue) -> list[JsonValue]:
    assert isinstance(value, list)
    return value


def _path(value: dict[str, JsonValue], *keys: str) -> JsonValue:
    """The value at ``keys``, each step an object of the producer's JSON schema."""
    found: JsonValue = value
    for key in keys:
        found = _object(found)[key]
    return found


def test_a_printed_exam_total_a_reply_lists_as_an_instruction_stays_header_metadata():
    listed, state = _build("heading", (("body:0000",), ("body:0004",)))
    unlisted, _ = _build("heading", (("body:0004",),))
    printed = printed_points_plan(state.chunks, state.questions)

    assert "body:0000" in printed.metadata
    assert printed.exam_total == 70
    assert _TOTAL not in _shown(listed)
    assert _lines(listed.document.instructions) == [_BOX, _CHECK]
    assert [item.points for item in listed.document.items] == [
        item.points for item in unlisted.document.items
    ]
    assert [item.points for item in listed.document.items] == [35, 35]


def test_a_printed_exam_total_the_grouping_calls_exam_wide_stays_header_metadata():
    result, state = _build("heading", (("body:0004",),), exam_wide_total=True)

    assert "body:0000" in printed_points_plan(state.chunks, state.questions).metadata
    assert _TOTAL not in _shown(result)
    assert _lines(result.document.instructions) == [_BOX, _CHECK]


_EXAM_WIDE_OWNERS = {"box": "body:0001", "name": _METADATA}


@pytest.mark.parametrize("governed", [_UNGOVERNED, _DEL_GOVERNS_BOTH], ids=["run", "governed"])
@pytest.mark.parametrize("del_kind", ["paragraph", "heading"])
@pytest.mark.parametrize("owner_kind", ["paragraph", "heading"])
@pytest.mark.parametrize("owner", sorted(_EXAM_WIDE_OWNERS))
def test_an_exam_wide_or_metadata_heading_never_opens_or_ends_a_section(
    owner, owner_kind, del_kind, governed
):
    headings = frozenset({_EXAM_WIDE_OWNERS[owner]}) if owner_kind == "heading" else frozenset()
    result, _ = _build(del_kind, _MIXED_BOX_NAME_DEL, headings=headings, governed=governed)
    document = result.document
    shown = _shown(result)

    assert _lines(document.instructions) == [_BOX, _CHECK]
    assert shown.count(_BOX) == 1
    assert not [line for line in shown if "Namn" in line]
    assert [_lines(parent.instruction) for parent in document.parents] == [[_DEL]]
    assert [len(parent.item_ids) for parent in document.parents] == [2]


@pytest.mark.parametrize("governed", [_UNGOVERNED, _DEL_GOVERNS_BOTH], ids=["run", "governed"])
@pytest.mark.parametrize("del_kind", ["paragraph", "heading"])
def test_a_printed_exam_total_listed_with_the_del_line_is_no_exam_text(del_kind, governed):
    mixed, state = _build(del_kind, (("body:0000", "body:0004"),), governed=governed)
    alone, _ = _build(del_kind, (("body:0004",),), governed=governed)
    shown = _shown(mixed)

    assert "body:0000" in printed_points_plan(state.chunks, state.questions).metadata
    assert not [line for line in shown if "Totalt" in line]
    assert _lines(mixed.document.instructions) == [_BOX, _CHECK]
    assert shown.count(_DEL) == 1
    assert [_lines(parent.instruction) for parent in mixed.document.parents] == [[_DEL]]
    assert mixed.document.header == alone.document.header
    assert [item.points for item in mixed.document.items] == [35, 35]
    assert [item.points for item in mixed.document.items] == [
        item.points for item in alone.document.items
    ]
