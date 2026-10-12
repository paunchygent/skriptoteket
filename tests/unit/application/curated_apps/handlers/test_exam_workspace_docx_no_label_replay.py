"""A question neither labeling pass labels becomes a review item the teacher labels.

``docx_build_v16_low19_no_label`` holds live recordings of a one-family-per-batch run, edited
so that the first pass refuses the question owning body:0085 and body:0086; the live second pass
answers unresolved (see its README). No converter request holds the question. It becomes one
review item holding its own chunks as printed, at its place, and no event reports the old
free_text route.
"""

import json

import pytest

from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_pipeline import (
    UNLABELED_REASON,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeParseOrigin,
    NativeTextSegment,
)
from skriptoteket.protocols.item_type_labeler import ItemTypeLabel
from tests.unit.application.curated_apps.handlers.docx_pipeline_replay import (
    FIXTURES,
    SecondWaveByAnchor,
    build_replay,
    corpus_chunks,
    recording,
)

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]

_ROOT = FIXTURES / "docx_build_v16_low19_no_label"
_EXAM = "svenska_2_kursavslutande_prov_med_facit"
_OWN = ("body:0085", "body:0086")


async def test_a_question_neither_pass_labels_becomes_a_source_review_item():
    answers = recording(_EXAM, "decisions_1", root=_ROOT)["answers"]
    assert isinstance(answers, list)
    assert {"type": "refusal", "name": "kind_q20"} in answers
    assert recording(_EXAM, "label_b_q20", root=_ROOT) == {"label": ItemTypeLabel.UNRESOLVED.value}

    provider = SecondWaveByAnchor(_EXAM, root=_ROOT)
    replay = build_replay(_EXAM, root=_ROOT, families_per_batch=1, provider=provider)
    outcome = await replay.pipeline.convert(job=replay.job())

    for request in provider.requests:
        if request.item_id.startswith("docx_w"):
            payload = json.loads(request.user_payload)
            assert not set(_OWN) & {chunk["anchor"] for chunk in payload["chunks"]}
    texts = {c.anchor: c.text for c in corpus_chunks(_EXAM)}
    (item,) = [i for i in outcome.result.document.items if i.source_anchor == "body:0085"]
    assert item.review.parse_origin is NativeParseOrigin.DETERMINISTIC
    assert item.review.reasons == (UNLABELED_REASON,)
    shown = [s.text for p in item.body for s in p.segments if isinstance(s, NativeTextSegment)]
    assert shown == [texts[a] for a in _OWN]
    assert outcome.update.item_ids["q20"][0] == item.item_id
    assert "no_label" not in {event.code for event in outcome.result.events}
