"""The unit DOCX replay serves second-pass labels only by their capture-time request key.

A ``label_b`` recording answers one exact request. A changed request, a recording whose stored
key no longer ends the request, and a recording without its ``.request.txt`` sidecar must never
be served (TASK-SKRIPT-REP-0046).
"""

from dataclasses import replace
from pathlib import Path

import pytest

from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_llm_contracts import (
    StructuredLLMEndpointKind,
    StructuredLLMProviderProfile,
    StructuredLLMRequest,
)
from tests.unit.application.curated_apps.handlers.docx_pipeline_replay import (
    RECORDINGS,
    MissingRecording,
    ReplayProvider,
    build_replay,
    recorded_exams,
    recording,
)

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]

_EXAM = "bf26_english_1_unit_test_kap_1_2_med_facit"
_PROFILE = StructuredLLMProviderProfile(
    "replay", "replay", StructuredLLMEndpointKind.RESPONSES, False, 4096, 1024
)
_LABELED_EXAMS = [e for e in recorded_exams() if any((RECORDINGS / e).glob("label_b_*.json"))]


async def _label_requests(exam: str) -> tuple[ReplayProvider, list[StructuredLLMRequest]]:
    replay = build_replay(exam)
    await replay.pipeline.convert(job=replay.job())
    labels = [r for r in replay.provider.requests if r.output_spec.schema_name == "item_type_label"]
    return replay.provider, labels


def _copy(name: str, directory: Path, *, key: str | None = None) -> None:
    source = RECORDINGS / _EXAM
    (directory / f"{name}.json").write_bytes((source / f"{name}.json").read_bytes())
    if key is not None:
        (directory / f"{name}.request.txt").write_text(f"{key}\n")


@pytest.mark.parametrize("exam", _LABELED_EXAMS)
async def test_every_label_request_is_served_its_own_recording_once(exam: str):
    provider, labels = await _label_requests(exam)
    recorded = sorted(p.stem for p in (RECORDINGS / exam).glob("label_b_*.json"))
    assert sorted(r.item_id.replace(":", "_") for r in labels) == recorded
    for request in labels:
        assert provider.recording_ids[request.item_id] == request.item_id.replace(":", "_")


async def test_a_changed_label_request_is_unmatched_and_the_original_is_served_once():
    _, labels = await _label_requests(_EXAM)
    request = labels[0]
    name = request.item_id.replace(":", "_")
    provider = ReplayProvider(_EXAM)

    changed = replace(request, user_payload=request.user_payload + " ")
    with pytest.raises(MissingRecording, match="no unused label_b recording"):
        await provider.complete_structured(request=changed, profile=_PROFILE)
    heading = "### Question q1\n"
    reworded = replace(
        request, user_payload=request.user_payload.replace(heading, f"{heading}Poäng: 1 poäng\n")
    )
    with pytest.raises(MissingRecording, match="no unused label_b recording"):
        await provider.complete_structured(request=reworded, profile=_PROFILE)
    assert provider.served == []

    response = await provider.complete_structured(request=request, profile=_PROFILE)
    assert response.content == recording(_EXAM, name)
    assert provider.served == [(request.item_id, name)]
    with pytest.raises(MissingRecording, match="no unused label_b recording"):
        await provider.complete_structured(request=request, profile=_PROFILE)


async def test_a_recording_whose_stored_key_no_longer_ends_the_request_is_not_served(tmp_path):
    _, labels = await _label_requests(_EXAM)
    request = labels[0]
    name = request.item_id.replace(":", "_")
    directory = tmp_path / _EXAM
    directory.mkdir()
    stored = (RECORDINGS / _EXAM / f"{name}.request.txt").read_text().removesuffix("\n")
    _copy(name, directory, key=stored + " (stale)")

    provider = ReplayProvider(_EXAM, root=tmp_path)
    with pytest.raises(MissingRecording, match="no unused label_b recording"):
        await provider.complete_structured(request=request, profile=_PROFILE)
    assert provider.served == []


async def test_a_label_recording_without_its_request_key_is_refused(tmp_path):
    directory = tmp_path / _EXAM
    directory.mkdir()
    keyed, unkeyed = sorted(p.stem for p in (RECORDINGS / _EXAM).glob("label_b_*.json"))[:2]
    stored = (RECORDINGS / _EXAM / f"{keyed}.request.txt").read_text().removesuffix("\n")
    _copy(keyed, directory, key=stored)
    _copy(unkeyed, directory)

    with pytest.raises(AssertionError, match=rf"missing sidecars for \['{unkeyed}'\]"):
        ReplayProvider(_EXAM, root=tmp_path)


async def test_a_request_key_without_its_recording_is_refused(tmp_path):
    directory = tmp_path / _EXAM
    directory.mkdir()
    (directory / "label_b_q999.request.txt").write_text("orphan key\n")

    with pytest.raises(AssertionError, match=r"unexpected sidecars for \['label_b_q999'\]"):
        ReplayProvider(_EXAM, root=tmp_path)
