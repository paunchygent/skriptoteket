"""The type-batched DOCX pipeline replayed from every exam's live recordings.

Each test builds the production pipeline with ``build_docx_conversion_pipeline`` over the
recordings in ``docx_build_v10/<exam>/`` and the corpus DOCX, then challenges the result.
"""

import json
import re

import pytest
from pydantic import JsonValue

from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_llm_contracts import (
    StructuredLLMBackendFailureCode,
    StructuredLLMProviderError,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_batches import question_families
from skriptoteket.domain.curated_apps.exam_workspace.docx_manifest import manifest_from_output
from skriptoteket.domain.curated_apps.exam_workspace.docx_source_rules import (
    points_line,
    title_without_answer_key,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamItemKind,
    NativeParseOrigin,
)
from tests.unit.application.curated_apps.handlers.docx_pipeline_replay import (
    build_replay,
    corpus_chunks,
    recorded_exams,
    recording,
)

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]

_GRAMMAR_1 = "svenska_2_grammatik_omprov_variant_1_med_facit"
_QUIZ = "chapter_4_poetry_and_lyrics_quiz_med_facit"


def _object(node: JsonValue) -> dict[str, JsonValue]:
    assert isinstance(node, dict)
    return node


def _list(node: JsonValue) -> list[JsonValue]:
    assert isinstance(node, list)
    return node


def _words(text: str) -> str:
    return " ".join(text.split())


async def _convert(exam: str, **options):
    replay = build_replay(exam, **options)
    return replay, await replay.pipeline.convert(job=replay.job())


def _manifest(exam: str):
    return manifest_from_output(recording(exam, "docx_grouping_1"), corpus_chunks(exam))


@pytest.mark.parametrize("exam", recorded_exams())
async def test_every_grouped_question_maps_to_items_once_and_in_source_order(exam: str):
    replay, outcome = await _convert(exam)
    update = outcome.update
    document = update.document
    grouped = [q.question_id for q in _manifest(exam).questions]

    assert list(update.item_ids) == grouped
    assert update.pending == ()
    assert set(update.filled) == set(grouped)
    assert all(update.item_ids[qid] for qid in grouped), "a grouped question lost all its items"
    mapped = [item_id for ids in update.item_ids.values() for item_id in ids]
    mapped += update.extra_item_ids
    assert sorted(mapped) == sorted(item.item_id for item in document.items)
    anchors = [item.source_anchor for item in document.items]
    assert len(set(anchors)) == len(anchors), "a chunk anchor starts two items"
    position = {chunk.anchor: index for index, chunk in enumerate(corpus_chunks(exam))}
    assert [position[a or ""] for a in anchors] == sorted(position[a or ""] for a in anchors)
    assert replay.progress.calls[0] == "outline"
    assert replay.progress.calls.count("batch_ready") == len(replay.progress.updates)


async def test_a_type_conflict_is_resent_and_leaves_its_neighbours_converted():
    replay, outcome = await _convert(_GRAMMAR_1)
    outline = {a: q.question_id for q in replay.progress.outlines[0].questions for a in q.anchors}
    second_wave = [
        request_id
        for request_id in replay.provider.request_ids
        if request_id.startswith("docx_w2-") and "c" not in request_id.removeprefix("docx_")
    ]
    items = [i for rid in second_wave for i in _list(recording(_GRAMMAR_1, rid)["items"])]
    conflicted = {
        outline[str(_list(_object(i)["source_anchors"])[0])]
        for i in items
        if _object(i)["outcome"] == "type_conflict"
    }
    converted = {
        outline[str(_list(_object(i)["source_anchors"])[0])]
        for i in items
        if _object(i)["outcome"] == "converted"
    }
    assert conflicted == {"q1"}
    assert {"q2", "q3", "q4"} <= converted

    assert replay.provider.request_ids.count("docx_w2-01-01c01") == 1
    after_conflict = next(u for u in replay.progress.updates if converted <= set(u.filled))
    assert "q1" in after_conflict.pending
    for qid in converted:
        assert after_conflict.item_ids[qid], f"{qid} lost its converted item to the release"
        item = next(
            i for i in after_conflict.document.items if i.item_id == after_conflict.item_ids[qid][0]
        )
        assert item.review.parse_origin is NativeParseOrigin.LLM_PARSED
    final = outcome.update
    q1_item = next(i for i in final.document.items if i.item_id == final.item_ids["q1"][0])
    assert q1_item.kind is NativeExamItemKind.FREE_TEXT
    assert q1_item.review.parse_origin is NativeParseOrigin.LLM_PARSED
    assert final.pending == ()


@pytest.mark.parametrize("exam", recorded_exams())
async def test_exam_title_is_the_text_of_the_groupings_title_chunks(exam: str):
    _, outcome = await _convert(exam)
    manifest = _manifest(exam)
    text = {chunk.anchor: chunk.text for chunk in corpus_chunks(exam)}
    assert manifest.title_anchors
    expected = title_without_answer_key(_words(" ".join(text[a] for a in manifest.title_anchors)))
    assert _words(outcome.update.document.title) == expected


def _unplaced_points_lines(exam: str):
    manifest = _manifest(exam)
    placed = {
        *(a for q in manifest.questions for a in (*q.anchors, *q.key_anchors)),
        *(c.anchor for c in manifest.contexts),
    }
    chunks = corpus_chunks(exam)
    position = {chunk.anchor: index for index, chunk in enumerate(chunks)}
    first = {q.question_id: position[q.anchors[0]] for q in manifest.questions}
    found = []
    for chunk in chunks:
        if chunk.anchor in placed or not points_line(chunk.text):
            continue
        before = [qid for qid, at in first.items() if at <= position[chunk.anchor]]
        if before:
            found.append((chunk, before[-1]))
    return manifest, found


@pytest.mark.parametrize("exam", [e for e in recorded_exams() if "grammatik" in e])
async def test_an_unplaced_points_line_belongs_to_the_question_before_it(exam: str):
    manifest, found = _unplaced_points_lines(exam)
    families = {f.question_id: f for f in question_families(manifest, corpus_chunks(exam))}
    assert found
    for chunk, previous in found:
        owners = [qid for qid, family in families.items() if chunk.anchor in family.claims]
        assert owners == [previous], f"{chunk.anchor} {chunk.text!r}"
    _, outcome = await _convert(exam)
    items = {item.item_id: item for item in outcome.update.document.items}
    for chunk, previous in found:
        match = re.search(r"\d+", chunk.text)
        assert match
        printed = int(match.group())
        assert [items[i].points for i in outcome.update.item_ids[previous]] == [printed]


@pytest.mark.parametrize("exam", recorded_exams())
async def test_each_batch_schema_names_only_its_own_anchors_and_kinds_without_ref_siblings(
    exam: str,
):
    replay, _ = await _convert(exam)
    batches = [r for r in replay.provider.requests if r.item_id.startswith("docx_w")]
    assert batches
    for request in batches:
        payload = json.loads(request.user_payload)
        own = {c["anchor"] for c in payload["chunks"]}
        schema = _object(request.output_spec.json_schema)
        defs = _object(schema["$defs"])
        lists = [
            _object(_object(schema["properties"])["answer_key_anchors"]),
            _object(_object(_object(defs["ProducedItem"])["properties"])["source_anchors"]),
            _object(_object(_object(defs["ProducedMetadata"])["properties"])["source_anchors"]),
        ]
        for node in lists:
            assert set(_list(_object(node["items"])["enum"])) == own, request.item_id
        kind = _object(_object(_object(defs["ProducedItem"])["properties"])["kind"])
        assert kind["enum"] == payload["item_kinds"], request.item_id
        assert not _ref_with_siblings(schema), request.item_id


def _ref_with_siblings(node: JsonValue, path: str = "$") -> list[str]:
    """Schema nodes holding ``$ref`` beside another keyword; strict mode rejects them."""
    if isinstance(node, list):
        return [
            p for i, entry in enumerate(node) for p in _ref_with_siblings(entry, f"{path}[{i}]")
        ]
    if not isinstance(node, dict):
        return []
    found = [path] if "$ref" in node and len(node) > 1 else []
    for key, value in node.items():
        if key in {"properties", "$defs"}:
            for name, child in _object(value).items():
                found += _ref_with_siblings(child, f"{path}.{key}.{name}")
        else:
            found += _ref_with_siblings(value, f"{path}.{key}")
    return found


async def test_a_provider_failure_turns_only_that_batchs_chunks_into_review_items():
    failing = "docx_w1-02"
    error = StructuredLLMProviderError(
        failure_code=StructuredLLMBackendFailureCode.PROVIDER_HTTP_ERROR,
        message="boom",
        provider_id="openai-gpt-6-luna",
        status_code=400,
    )
    replay, outcome = await _convert(_QUIZ, failures={failing: error})
    request = next(r for r in replay.provider.requests if r.item_id == failing)
    lost = {c["anchor"]: c["text"] for c in json.loads(request.user_payload)["chunks"]}
    assert lost
    document = outcome.update.document
    chunk_text = {c.anchor: c.text for c in corpus_chunks(_QUIZ)}

    lost_items = [i for i in document.items if i.source_anchor in lost]
    assert lost_items
    for item in lost_items:
        assert item.review.parse_origin is not NativeParseOrigin.LLM_PARSED
        assert item.review.reasons
    shown = _words(" ".join(line for i in lost_items for line in i.plain_text_lines()))
    for anchor, text in lost.items():
        assert _words(chunk_text[anchor]) in shown, f"{anchor} lost its source text"
    others = [i for i in document.items if i.source_anchor not in lost]
    assert others
    assert all(i.review.parse_origin is NativeParseOrigin.LLM_PARSED for i in others)
    assert any(
        e.code == StructuredLLMBackendFailureCode.PROVIDER_HTTP_ERROR.value
        for e in outcome.result.events
    )
    assert outcome.update.pending == ()
