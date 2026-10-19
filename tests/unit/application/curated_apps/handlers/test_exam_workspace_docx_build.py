"""The type-batched DOCX pipeline replayed from every exam's live recordings.

Each test builds the production pipeline with ``build_docx_conversion_pipeline`` over the
recordings in ``docx_key_provenance_v14/<exam>/`` and the corpus DOCX, then challenges
admission and provenance contracts, not exact equality with the gold exam.
"""

import json
from dataclasses import replace

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
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeParseOrigin,
)
from tests.unit.application.curated_apps.handlers.docx_pipeline_replay import (
    RECORDINGS,
    MissingRecording,
    ReplayProvider,
    build_replay,
    corpus_chunks,
    recorded_exams,
    recording,
)

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]

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
    assert all(len(update.item_ids[qid]) == 1 for qid in grouped), "a question is not one item"
    mapped = [item_id for ids in update.item_ids.values() for item_id in ids]
    mapped += update.extra_item_ids
    assert sorted(mapped) == sorted(item.item_id for item in document.items)
    anchors = [item.source_anchor for item in document.items]
    assert len(set(anchors)) == len(anchors), "a chunk anchor starts two items"
    position = {chunk.anchor: index for index, chunk in enumerate(corpus_chunks(exam))}
    assert [position[a or ""] for a in anchors] == sorted(position[a or ""] for a in anchors)
    assert replay.progress.calls[0] == "outline"
    assert replay.progress.calls.count("batch_ready") == len(replay.progress.updates)
    request_ids = [request_id for request_id, _ in replay.provider.served]
    assert len(request_ids) == len(set(request_ids)), "a request id was served twice"
    served = [name for _, name in replay.provider.served]
    assert len(served) == len(set(served)), "a producer reply was replayed twice"
    assert set(served) == {
        path.stem
        for path in (RECORDINGS / exam).glob("*.json")
        if not path.stem.startswith("decisions_")
    }


@pytest.mark.parametrize("wave", ["docx_w1-", "docx_w2-"])
async def test_replay_batches_require_visible_anchors_and_an_unused_recording(wave: str, tmp_path):
    """Isolate one unmodified reply to challenge both converter waves' replay boundary."""
    from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_llm_contracts import (
        StructuredLLMEndpointKind,
        StructuredLLMProviderProfile,
    )

    exam = "bf26_english_1_unit_test_kap_1_2_med_facit"
    replay, _ = await _convert(exam)
    request = next(r for r in replay.provider.requests if r.item_id.startswith(wave))
    name = replay.provider.recording_ids[request.item_id]
    directory = tmp_path / exam
    directory.mkdir()
    (directory / f"{name}.json").write_bytes((RECORDINGS / exam / f"{name}.json").read_bytes())
    (directory / "docx_grouping_1.json").write_bytes(
        (RECORDINGS / exam / "docx_grouping_1.json").read_bytes()
    )
    provider = ReplayProvider(exam, root=tmp_path)
    profile = StructuredLLMProviderProfile(
        "replay", "replay", StructuredLLMEndpointKind.RESPONSES, False, 4096, 1024
    )
    invisible = replace(
        request,
        user_payload=json.dumps({"chunks": [{"anchor": "body:9999"}], "context_chunks": []}),
    )
    with pytest.raises(MissingRecording, match="no unused batch reply"):
        await provider.complete_structured(request=invisible, profile=profile)
    assert provider.served == []

    context_only = replace(
        request,
        user_payload=json.dumps(
            {
                "chunks": [{"anchor": "body:9999"}],
                "context_chunks": json.loads(request.user_payload)["chunks"],
            }
        ),
    )
    with pytest.raises(MissingRecording, match="no unused batch reply"):
        await provider.complete_structured(request=context_only, profile=profile)
    assert provider.served == []

    response = await provider.complete_structured(request=request, profile=profile)
    assert response.content == recording(exam, name)
    with pytest.raises(MissingRecording, match="no unused batch reply"):
        await provider.complete_structured(request=request, profile=profile)
    assert provider.served == [(request.item_id, name)]

    # A pre-change build may cite a header omitted from the current conversion batch.
    grouping = recording(exam, "docx_grouping_1", tmp_path)
    grouping["header_anchors"] = [{"anchor": "recorded_header", "kind": "course", "governs": []}]
    (directory / "docx_grouping_1.json").write_text(json.dumps(grouping))
    reply = recording(exam, name, tmp_path)
    reply["answer_key_anchors"] = [*_list(reply["answer_key_anchors"]), "recorded_header"]
    (directory / f"{name}.json").write_text(json.dumps(reply))
    header_provider = ReplayProvider(exam, root=tmp_path)
    response = await header_provider.complete_structured(request=request, profile=profile)
    assert response.content == reply
    # The exception is only for recorded headers, not arbitrary unseen source anchors.
    reply["answer_key_anchors"] = [*_list(reply["answer_key_anchors"]), "unseen_non_header"]
    (directory / f"{name}.json").write_text(json.dumps(reply))
    with pytest.raises(MissingRecording, match="no unused batch reply"):
        await ReplayProvider(exam, root=tmp_path).complete_structured(
            request=request, profile=profile
        )


@pytest.mark.parametrize("exam", recorded_exams())
async def test_admitted_keys_keep_the_recorded_provenance_and_facit(exam: str):
    replay, outcome = await _convert(exam)
    from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import ProducedItem

    origins = {
        "copied": "source_provided",
        "interpreted": "ai_interpreted",
        "invented": "machine_proposed",
        None: "absent",
    }
    produced = {}
    for request in replay.provider.requests:
        if not request.item_id.startswith("docx_w"):
            continue
        # Typed resends have live replies too; missing recordings must not silently
        # replace the producer outcome with a source review item.
        assert request.item_id in replay.provider.recording_ids
        for raw in _list(recording(exam, replay.provider.recording_ids[request.item_id])["items"]):
            node = _object(raw)
            if node["outcome"] == "converted":
                # Admission rejects invalid producer items; only native LLM items below
                # must have a valid current producer counterpart.
                produced[str(_list(node["source_anchors"])[0])] = node
    admitted = [
        i
        for i in outcome.result.document.items
        if i.review.parse_origin is NativeParseOrigin.LLM_PARSED
    ]
    assert admitted
    for item in admitted:
        assert item.source_anchor is not None
        producer = ProducedItem.model_validate(produced[item.source_anchor])
        expected = (
            "not_applicable" if producer.kind.value == "free_text" else origins[producer.key_source]
        )
        assert item.answer_key.origin.value == expected
        # The facit keeps the teacher's wording; the source's italic tags are not wording.
        facit = producer.facit_text
        assert item.facit_text == (facit.replace("<i>", "").replace("</i>", "") if facit else facit)
        assert "<i>" not in (item.facit_text or "")


async def test_recorded_typed_resend_retains_an_incomplete_key_for_teacher_review():
    exam = "bf26_english_1_unit_test_kap_1_2_med_facit"
    replay, outcome = await _convert(exam)

    assert replay.provider.recording_ids["docx_w2-10-01"] == "docx_w2-11-01"
    assert replay.provider.recording_ids["docx_w2-10-01c01"] == "docx_w2-11-01c01"
    assert [r for r in replay.provider.request_ids if r.startswith("docx_w2-10-01")] == [
        "docx_w2-10-01",
        "docx_w2-10-01c01",
    ]
    (item,) = [i for i in outcome.update.document.items if i.source_anchor == "body:0115"]
    assert item.review.parse_origin is NativeParseOrigin.SOURCE_FALLBACK
    assert item.review.reasons
    assert item.retry_source is not None
    assert [c.anchor for c in item.retry_source.chunks] == ["body:0115"]
    assert [c.anchor for c in item.retry_source.key_chunks] == ["body:0116"]
    assert item.retry_source.key_chunks[0].text == "Correct answer: its"
    codes = [e.code for e in outcome.result.events if "body:0115" in e.anchors]
    assert "type_conflict_kept" in codes
    assert "item_unparsed" in codes


@pytest.mark.parametrize("exam", recorded_exams())
async def test_automatic_spellings_obey_distance_disjointness_and_quota(exam: str):
    from skriptoteket.domain.curated_apps.exam_workspace.answer_spelling import (
        filter_answer_spelling_candidates,
        is_allowed_answer_spelling_variant,
        normalize_answer,
    )

    _, outcome = await _convert(exam)
    gaps = [gap for item in outcome.result.document.items for gap in item.gaps]
    for gap in gaps:
        assert set(map(normalize_answer, gap.accepted_values)).isdisjoint(
            map(normalize_answer, gap.automatic_values)
        )
        assert (
            filter_answer_spelling_candidates(gap.accepted_values, gap.automatic_values)
            == gap.automatic_values
        )
        for candidate in gap.automatic_values:
            assert any(
                is_allowed_answer_spelling_variant(
                    answer, candidate, other_gold_answers=gap.accepted_values
                )
                for answer in gap.accepted_values
            )


@pytest.mark.parametrize("exam", recorded_exams())
async def test_grouping_title_anchors_name_source_text_without_the_facit_label(exam: str):
    _, outcome = await _convert(exam)
    manifest = _manifest(exam)
    text = {chunk.anchor: chunk.text for chunk in corpus_chunks(exam)}
    assert manifest.title_anchors
    expected = title_without_answer_key(_words(" ".join(text[a] for a in manifest.title_anchors)))
    title = _words(outcome.result.document.title)
    assert title == expected
    assert title
    assert "med facit" not in title.casefold()
    assert "answer key" not in title.casefold()


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
        assert request.output_spec.schema_version == "docx_exam_build_v14"
        item_schema = _object(defs["ProducedItem"])
        assert {"key_source", "facit_text"} <= set(_list(item_schema["required"]))
        segment_schema = _object(defs["ProducedSegment"])
        shapes = (
            [_object(shape) for shape in _list(segment_schema["anyOf"])]
            if "anyOf" in segment_schema
            else [segment_schema]
        )
        assert all("spelling_candidates" not in _list(shape["required"]) for shape in shapes)
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


@pytest.mark.parametrize("exam", recorded_exams())
async def test_recorded_source_classes_agree_with_the_manually_audited_facit(exam: str):
    """The live audit found explicit answer words/letters, not invented or inferred keys.

    Inline Swedish answer slots were checked against the DOCX italic runs. This
    explicit expectation must be re-audited, not inferred from a model's own label.
    Free-text marking guides have no objective-key provenance.
    """
    paths = sorted((RECORDINGS / exam).glob("docx_w*.json"))
    assert paths
    for path in paths:
        for raw in _list(recording(exam, path.stem)["items"]):
            node = _object(raw)
            expected = None if node["kind"] == "free_text" else "copied"
            assert node["key_source"] == expected, (exam, path.name, node["source_anchors"])
            if expected == "copied":
                assert isinstance(node["facit_text"], str) and node["facit_text"].strip()


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
        # Trailing points wording equal to the item's points leaves the body (D2, D6);
        # every other lost chunk shows verbatim. Expected texts are literals.
        expected = {
            "body:0080": "Part 2B: stanza",
            "body:0086": "Part 2B: tone",
            "body:0092": "Part 2B: rhythm",
            "body:0098": "Part 2B: theme",
            "body:0104": "Part 2B: symbolism",
        }.get(anchor, chunk_text[anchor])
        assert _words(expected) in shown, f"{anchor} lost its source text"
    others = [i for i in document.items if i.source_anchor not in lost]
    assert others
    assert all(i.review.parse_origin is NativeParseOrigin.LLM_PARSED for i in others)
    assert any(
        e.code == StructuredLLMBackendFailureCode.PROVIDER_HTTP_ERROR.value
        for e in outcome.result.events
    )
    assert outcome.update.pending == ()


@pytest.mark.parametrize("exam", recorded_exams())
async def test_questions_one_context_governs_share_one_parent_whatever_their_kinds(exam: str):
    _, outcome = await _convert(exam)
    update = outcome.update
    assert not [e for e in outcome.result.events if e.code == "parent_differs_from_grouping"]
    for context in _manifest(exam).contexts:
        governed = [q for q in context.governs if update.item_ids.get(q)]
        parents = {update.parent_ids.get(q) for q in governed}
        if len(governed) >= 2:
            assert len(parents) == 1 and None not in parents, context.anchor
