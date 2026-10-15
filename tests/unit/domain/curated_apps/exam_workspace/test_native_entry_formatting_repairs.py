"""Source labels are accounted for by their actual native choice/match entries."""

from dataclasses import replace

import pytest

from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_build import native_item
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import ProducedItem
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import (
    DocxChunk,
    DocxSourceParagraph,
    DocxSourceRun,
)
from skriptoteket.domain.curated_apps.exam_workspace.shared_body import body_plain_text

pytestmark = pytest.mark.unit


def _source(anchor, lines, *, kind="paragraph", separator="\n", one_paragraph=False):
    text = separator.join(line for line, _ in lines)
    runs = []
    paragraphs = []
    offset = 0
    for line, label in lines:
        runs.append(DocxSourceRun(offset, label, ("bold",)))
        runs.append(DocxSourceRun(offset + len(label), line[len(label) :], ()))
        paragraphs.append(DocxSourceParagraph(offset, line, None))
        offset += len(line) + len(separator)
    if one_paragraph:
        paragraphs = [DocxSourceParagraph(0, text, None)]
    return DocxChunk(anchor, kind, text, text, runs=tuple(runs), paragraphs=tuple(paragraphs))


def _item(kind, chunks, **entries):
    return ProducedItem.model_validate(
        {
            "source_anchors": [chunk.anchor for chunk in chunks],
            "outcome": "converted",
            "review_reason": None,
            "kind": kind,
            "body": [
                {"segments": [{"kind": "text", "text": "Choose an answer.", "accepted_values": []}]}
            ],
            "key_source": None,
            "facit_text": None,
            "points": None,
            "choices": [],
            **entries,
        }
    )


def test_native_choices_account_for_each_marked_source_label_in_one_chunk():
    prompt = _source("body:0001", [("Choose an answer.", "")])
    options = _source("body:0002", [("A. red", "A."), ("B. blue", "B.")])
    chunks = (prompt, options)
    paths = []
    result = native_item(
        _item(
            "single_choice",
            chunks,
            choices=[{"text": "red", "correct": False}, {"text": "blue", "correct": False}],
        ),
        chunks=chunks,
        language="en",
        formatting_observer=paths.append,
    )
    assert paths == ["exact"]
    assert [body_plain_text(choice.body) for choice in result.choices] == ["red", "blue"]
    assert body_plain_text(result.body) == "Choose an answer."


def test_native_matching_accounts_for_marked_row_and_column_entry_labels():
    prompt = _source("body:0001", [("Choose an answer.", "")])
    entries = _source(
        "body:0002",
        [("1. red", "1."), ("A. warm", "A."), ("2. blue", "2."), ("B. cold", "B.")],
        kind="table",
    )
    chunks = (prompt, entries)
    paths = []
    result = native_item(
        _item("matching", chunks, match_left=["red", "blue"], match_right=["warm", "cold"]),
        chunks=chunks,
        language="en",
        formatting_observer=paths.append,
    )
    assert paths == ["exact"]
    assert [body_plain_text(entry.body) for entry in result.match_left] == ["red", "blue"]
    assert [body_plain_text(entry.body) for entry in result.match_right] == ["warm", "cold"]
    assert body_plain_text(result.body) == "Choose an answer."


@pytest.mark.parametrize("prefix", ["Safety.", "a) Safety.", "A"])
@pytest.mark.parametrize("layout", ["paragraph", "line", "inline", "table"])
def test_choice_rebuild_restores_marked_content_before_its_aligned_wording(prefix, layout):
    prompt = _source("body:0001", [("Choose an answer.", "")])
    shown = "crid fumes" if prefix == "A" else "Do not mix acids."
    original = prefix + ("" if prefix == "A" else " ") + shown
    options = _source(
        "body:0002",
        [(original, prefix), ("b) blue", "b)")],
        kind="table" if layout == "table" else "paragraph",
        separator={"inline": " ", "table": " | "}.get(layout, "\n"),
        one_paragraph=layout in {"line", "inline"},
    )
    chunks = (prompt, options)
    paths = []
    result = native_item(
        _item(
            "single_choice",
            chunks,
            choices=[{"text": shown, "correct": False}, {"text": "blue", "correct": False}],
        ),
        chunks=chunks,
        language="en",
        formatting_observer=paths.append,
    )
    expected = original.removeprefix("a) ")
    assert body_plain_text(result.choices[0].body) == expected
    assert result.choices[0].body[0].segments[0].marks == ("bold",)
    assert body_plain_text(result.choices[1].body) == "blue"
    assert body_plain_text(result.body) == "Choose an answer."
    assert paths == ["rebuilt"]


def test_matching_rebuilds_missing_marked_words_on_each_entry_side():
    prompt = _source("body:0001", [("Choose an answer.", "")])
    cells = _source(
        "body:0002",
        [
            ("1. Safety. red", "1. Safety."),
            ("A. Caution. warm", "A. Caution."),
            ("2. blue", "2."),
            ("B. cold", "B."),
        ],
        kind="table",
        separator=" | ",
    )
    chunks = (prompt, cells)
    result = native_item(
        _item("matching", chunks, match_left=["red", "blue"], match_right=["warm", "cold"]),
        chunks=chunks,
        language="en",
    )
    assert [body_plain_text(entry.body) for entry in result.match_left] == ["Safety. red", "blue"]
    assert [body_plain_text(entry.body) for entry in result.match_right] == [
        "Caution. warm",
        "cold",
    ]
    assert result.match_left[0].body[0].segments[0].marks == ("bold",)
    assert result.match_right[0].body[0].segments[0].marks == ("bold",)
    assert body_plain_text(result.body) == "Choose an answer."


def test_native_item_rebuilds_all_identified_text_when_heading_alignment_has_no_winner():
    heading = _source("body:0001", [("Read this section carefully.", "")])
    heading = replace(
        heading,
        paragraphs=(DocxSourceParagraph(0, heading.text, 2),),
    )
    question = _source("body:0002", [("Answer the question.", "")])
    chunks = (heading, question)
    paths = []
    result = native_item(
        _item(
            "free_text",
            chunks,
            body=[
                {
                    "segments": [
                        {"kind": "text", "text": "Follow these guidelines.", "accepted_values": []}
                    ]
                }
            ],
        ),
        chunks=chunks,
        language="en",
        formatting_observer=paths.append,
    )
    assert paths == ["rebuilt"]
    assert [paragraph.heading_level for paragraph in result.body] == [2, None]
    assert body_plain_text(result.body) == "Read this section carefully.\nAnswer the question."
