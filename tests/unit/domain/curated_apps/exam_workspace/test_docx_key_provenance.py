"""Current-format synthetic producer replies challenge provenance and spelling admission."""

import pytest
from pydantic import ValidationError

from skriptoteket.domain.curated_apps.exam_workspace.answer_spelling import (
    filter_answer_spelling_candidates,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_build import aligned_native_item
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import (
    ProducedCriterion,
    ProducedItem,
    ProducedParagraph,
    ProducedSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_schema import docx_build_output_spec
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_criteria import (
    NativeExamCriterion,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeAnswerKeyOrigin,
    NativeExamItemKind,
)

pytestmark = pytest.mark.unit


def _gap_item(
    source: str | None, facit: str | None, *, answers: tuple[str, ...] = ("katt",)
) -> ProducedItem:
    return ProducedItem.model_validate(
        {
            "source_anchors": ["body:0001"],
            "outcome": "converted",
            "review_reason": None,
            "kind": "gap_fill",
            "key_source": source,
            "facit_text": facit,
            "points": 1,
            "choices": [],
            "body": [
                {
                    "segments": [
                        {
                            "kind": "gap",
                            "text": None,
                            "accepted_values": answers,
                        }
                    ]
                }
            ],
        }
    )


@pytest.mark.parametrize(
    ("source", "facit", "origin"),
    [
        ("copied", "katt", NativeAnswerKeyOrigin.SOURCE_PROVIDED),
        ("interpreted", "Djuret som eftersöks är en katt.", NativeAnswerKeyOrigin.AI_INTERPRETED),
        ("invented", None, NativeAnswerKeyOrigin.MACHINE_PROPOSED),
        (None, "Svaret är otydligt.", NativeAnswerKeyOrigin.ABSENT),
    ],
)
def test_key_source_maps_without_treating_invented_answers_as_teacher_keys(
    source: str | None, facit: str | None, origin: NativeAnswerKeyOrigin, monkeypatch
) -> None:
    monkeypatch.setattr(
        "skriptoteket.domain.curated_apps.exam_workspace.docx_ai_gap_values.produce_answer_misspellings",
        lambda *_, **__: ("KATT", "kat", "kattn", "ktat", "hund", "kattnn"),
    )
    item = aligned_native_item(
        _gap_item(source, facit, answers=() if source is None else ("katt",)), language="sv"
    ).item
    assert item.answer_key.origin is origin
    assert item.facit_text == facit
    # The producer supplies candidates for every keyed gap, invented keys included; the
    # native contract keeps the bounded ones in producer order.
    assert item.gaps[0].automatic_values == (("kat", "kattn", "ktat") if source is not None else ())


@pytest.mark.parametrize(
    ("source", "facit", "answers"),
    [
        ("copied", None, ("katt",)),
        ("interpreted", None, ("katt",)),
        ("invented", "katt", ("katt",)),
        (None, "katt", ("katt",)),
        ("copied", "katt", ()),
        ("copied", "  ", ("katt",)),
    ],
)
def test_contradictory_provenance_is_not_admitted(
    source: str | None, facit: str | None, answers: tuple[str, ...]
) -> None:
    with pytest.raises(ValidationError):
        _gap_item(source, facit, answers=answers)


def test_spelling_filter_distances_deduplication_and_quota_are_per_answer() -> None:
    assert filter_answer_spelling_candidates(
        ("katt", "Stockholm"),
        (
            "KATT",
            "kat",
            " KAT ",
            "ktat",
            "kattn",
            "kattx",
            "kattnn",
            "Stockhlom",
            "Stockhlm",
            "Stokhlm",
            "hund",
        ),
    ) == ("kat", "ktat", "kattn", "Stockhlom", "Stockhlm", "Stokhlm")
    assert filter_answer_spelling_candidates(("katt", "kat"), ("KAT", "KATT", "  ")) == ()


def test_current_producer_schema_requires_new_fields_and_has_no_old_payload_reader() -> None:
    item = _gap_item("copied", "katt")
    legacy = item.model_dump()
    del legacy["key_source"]
    del legacy["facit_text"]
    with pytest.raises(ValidationError):
        ProducedItem.model_validate(legacy)
    with pytest.raises(ValidationError):
        ProducedSegment.model_validate(
            {
                "kind": "gap",
                "text": None,
                "accepted_values": ["katt"],
                "spelling_candidates": [],
            }
        )
    spec = docx_build_output_spec(anchors=("body:0001",), kinds=(NativeExamItemKind.GAP_FILL,))
    assert spec.schema_version == "docx_exam_build_v14"
    definitions = spec.json_schema["$defs"]
    assert isinstance(definitions, dict)
    item_node = definitions["ProducedItem"]
    assert isinstance(item_node, dict)
    required = item_node["required"]
    assert isinstance(required, list)
    assert "key_source" in required
    assert "facit_text" in required


@pytest.mark.parametrize("kind", ["single_choice", "multiple_response", "matching"])
@pytest.mark.parametrize("source", ["copied", "interpreted", "invented"])
def test_choice_and_matching_keys_use_the_same_provenance_mapping(kind: str, source: str) -> None:
    payload = _gap_item("copied", "katt").model_dump()
    payload.update(
        kind=kind,
        key_source=source,
        facit_text=None if source == "invented" else "A",
        body=[
            {
                "segments": [
                    {
                        "kind": "text",
                        "text": "Välj.",
                        "accepted_values": [],
                    }
                ]
            }
        ],
    )
    if kind == "matching":
        payload.update(
            match_left=["Katt"],
            match_right=["Djur", "Fordon"],
            match_pairs=[{"left": "Katt", "right": "Djur"}],
        )
    else:
        payload["choices"] = [{"text": "Katt", "correct": True}, {"text": "Bil", "correct": False}]
    item = aligned_native_item(ProducedItem.model_validate(payload), language="sv").item
    assert (
        item.answer_key.origin.value
        == {
            "copied": "source_provided",
            "interpreted": "ai_interpreted",
            "invented": "machine_proposed",
        }[source]
    )


def test_a_removed_spelling_candidate_field_is_rejected() -> None:
    with pytest.raises(ValidationError):
        ProducedSegment.model_validate(
            {"kind": "text", "text": "Läs", "accepted_values": [], "spelling_candidates": []}
        )


def test_free_text_retains_facit_but_has_no_objective_key_source() -> None:
    item = ProducedItem(
        source_anchors=("body:0001",),
        outcome="converted",
        review_reason=None,
        kind=NativeExamItemKind.FREE_TEXT,
        key_source=None,
        facit_text="Bedöm resonemanget.",
        criteria=(ProducedCriterion(text="Bedöm resonemanget."),),
        points=None,
        choices=(),
        body=(
            ProducedParagraph(
                segments=(ProducedSegment(kind="text", text="Resonera.", accepted_values=()),)
            ),
        ),
    )
    native = aligned_native_item(item, language="sv").item
    assert native.facit_text == item.facit_text
    assert native.answer_key.origin is NativeAnswerKeyOrigin.NOT_APPLICABLE
    # R14: a guide without per-criterion points is one estimated criterion at 1 point
    # when the question prints none.
    assert native.criteria == (NativeExamCriterion(text="Bedöm resonemanget.", points=1),)
    assert native.points == 1
    assert native.points_estimated is True
