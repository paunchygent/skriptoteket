"""DOCX conversion draws automatic gap spellings from the shared producer.

One language comes from the whole document. The model no longer proposes spelling
candidates: a keyed gap's automatic values come from ``produce_answer_misspellings`` with
the language inferred once from the whole extracted document text and the item's other
gold answers as exclusions, invented keys included.
"""

from uuid import uuid4

import pytest
from pydantic import JsonValue

from skriptoteket.application.curated_apps.handlers import exam_workspace_docx_build_state
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_admission import (
    admit_batch,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_state import (
    DocxBuildState,
)
from skriptoteket.domain.curated_apps.exam_workspace import docx_ai_gap_values
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_build import aligned_native_item
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import ProducedItem
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.exam_document_language import Language
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeAnswerKeyOrigin,
)

pytestmark = pytest.mark.unit


def _chunk(anchor: str, text: str) -> DocxChunk:
    return DocxChunk(anchor, "paragraph", text, text)


def _state(*texts: str) -> DocxBuildState:
    chunks = tuple(_chunk(f"body:{n:04d}", text) for n, text in enumerate(texts, start=1))
    return DocxBuildState(
        job_id=uuid4(),
        document_id=uuid4(),
        filename="prov.docx",
        source_sha256="0" * 64,
        chunks=chunks,
        questions=(tuple(c.anchor for c in chunks),),
    )


def _record_producer(
    monkeypatch: pytest.MonkeyPatch, returns: tuple[str, ...] = ()
) -> list[dict[str, object]]:
    calls: list[dict[str, object]] = []

    def fake(
        accepted_values: tuple[str, ...],
        *,
        language: Language,
        other_gold_answers: tuple[str, ...] = (),
    ) -> tuple[str, ...]:
        calls.append(
            {
                "accepted_values": accepted_values,
                "language": language,
                "other_gold_answers": other_gold_answers,
            }
        )
        return returns

    monkeypatch.setattr(docx_ai_gap_values, "produce_answer_misspellings", fake)
    return calls


def _gap_item(gaps: tuple[tuple[str, ...], ...], *, key_source: str = "invented") -> ProducedItem:
    segments: list[JsonValue] = []
    for index, accepted in enumerate(gaps):
        segments.append({"kind": "text", "text": f"Part {index}. ", "accepted_values": []})
        segments.append({"kind": "gap", "text": None, "accepted_values": list(accepted)})
    return ProducedItem.model_validate(
        {
            "source_anchors": ["body:0001"],
            "outcome": "converted",
            "conflict_kind": None,
            "review_reason": None,
            "kind": "gap_fill",
            "printed_label": None,
            "key_source": key_source,
            "facit_text": None if key_source == "invented" else "play",
            "body": [{"segments": segments}],
            "points": None,
            "choices": [],
            "match_left": [],
            "match_right": [],
            "match_pairs": [],
            "criteria": [],
        }
    )


def test_state_infers_one_language_from_the_whole_extracted_document_text(monkeypatch) -> None:
    seen: list[str] = []

    def fake(text: str) -> Language:
        seen.append(text)
        return "en"

    monkeypatch.setattr(exam_workspace_docx_build_state, "infer_exam_document_language", fake)

    state = _state("First paragraph.", "Second paragraph.")

    assert state.language == "en"
    assert seen == ["First paragraph.\nSecond paragraph."]


def test_every_keyed_gap_reaches_the_producer_with_the_language_and_its_other_gold(
    monkeypatch,
) -> None:
    calls = _record_producer(monkeypatch)

    item = aligned_native_item(
        _gap_item((("katt", "katten"), ("hund",))), language="en", foreign_chunks=()
    ).item

    assert calls == [
        {
            "accepted_values": ("katt", "katten"),
            "language": "en",
            "other_gold_answers": ("hund",),
        },
        {
            "accepted_values": ("hund",),
            "language": "en",
            "other_gold_answers": ("katt", "katten"),
        },
    ]
    assert [gap.automatic_values for gap in item.gaps] == [(), ()]


def test_an_invented_key_gets_producer_misspellings_bounded_by_the_native_contract(
    monkeypatch,
) -> None:
    _record_producer(monkeypatch, returns=("KATT", "kat", "kattx", "hund", "katt"))

    item = aligned_native_item(_gap_item((("katt",),)), language="sv", foreign_chunks=()).item

    assert item.answer_key.origin is NativeAnswerKeyOrigin.MACHINE_PROPOSED
    assert item.gaps[0].accepted_values == ("katt",)
    assert item.gaps[0].automatic_values == ("kat", "kattx")


def test_admission_gives_the_states_document_language_to_the_gap_producer(monkeypatch) -> None:
    calls = _record_producer(monkeypatch, returns=("Stokholm",))
    state = _state("The bands play at the festival.")
    body: JsonValue = [
        {
            "segments": [
                {"kind": "text", "text": "The bands ", "accepted_values": []},
                {"kind": "gap", "text": None, "accepted_values": ["Stockholm"]},
                {"kind": "text", "text": " at the festival.", "accepted_values": []},
            ]
        }
    ]

    admit_batch(
        {
            "title": None,
            "instructions": [],
            "answer_key_anchors": [],
            "items": [
                {
                    "source_anchors": ["body:0001"],
                    "outcome": "converted",
                    "conflict_kind": None,
                    "review_reason": None,
                    "kind": "gap_fill",
                    "printed_label": None,
                    "key_source": "invented",
                    "facit_text": None,
                    "body": body,
                    "points": None,
                    "choices": [],
                    "match_left": [],
                    "match_right": [],
                    "match_pairs": [],
                    "criteria": [],
                }
            ],
        },
        state,
    )

    ((item, anchors),) = [(a.item, h) for a, h in state.accepted]
    assert anchors == ("body:0001",)
    assert calls == [
        {"accepted_values": ("Stockholm",), "language": "en", "other_gold_answers": ()}
    ]
    assert item.gaps[0].automatic_values == ("Stokholm",)
