"""Source labels are accounted for by their actual native choice/match entries."""

from dataclasses import replace

import pytest

from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_item import aligned_native_item
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import (
    DocxChunk,
    DocxSourceParagraph,
    DocxSourceRun,
)
from skriptoteket.domain.curated_apps.exam_workspace.shared_body import body_plain_text
from tests.unit.domain.curated_apps.exam_workspace.native_entry_formatting_test_support import (
    _as_text,
    _item,
    _source,
)

pytestmark = pytest.mark.unit


def test_native_choices_account_for_each_marked_source_label_in_one_chunk():
    prompt = _source("body:0001", [("Choose an answer.", "")])
    options = _source("body:0002", [("A. red", "A."), ("B. blue", "B.")])
    chunks = (prompt, options)
    paths: list[str] = []
    result = aligned_native_item(
        _item(
            "single_choice",
            chunks,
            choices=[{"text": "red", "correct": False}, {"text": "blue", "correct": False}],
        ),
        chunks=chunks,
        language="en",
        formatting_observer=paths.append,
        foreign_chunks=(),
    ).item
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
    paths: list[str] = []
    result = aligned_native_item(
        _item("matching", chunks, match_left=["red", "blue"], match_right=["warm", "cold"]),
        chunks=chunks,
        language="en",
        formatting_observer=paths.append,
        foreign_chunks=(),
    ).item
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
    paths: list[str] = []
    result = aligned_native_item(
        _item(
            "single_choice",
            chunks,
            choices=[{"text": shown, "correct": False}, {"text": "blue", "correct": False}],
        ),
        chunks=chunks,
        language="en",
        formatting_observer=paths.append,
        foreign_chunks=(),
    ).item
    expected = original.removeprefix("a) ")
    assert body_plain_text(result.choices[0].body) == expected
    assert _as_text(result.choices[0].body[0].segments[0]).marks == ("bold",)
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
    result = aligned_native_item(
        _item("matching", chunks, match_left=["red", "blue"], match_right=["warm", "cold"]),
        chunks=chunks,
        language="en",
        foreign_chunks=(),
    ).item
    assert [body_plain_text(entry.body) for entry in result.match_left] == ["Safety. red", "blue"]
    assert [body_plain_text(entry.body) for entry in result.match_right] == [
        "Caution. warm",
        "cold",
    ]
    assert _as_text(result.match_left[0].body[0].segments[0]).marks == ("bold",)
    assert _as_text(result.match_right[0].body[0].segments[0]).marks == ("bold",)
    assert body_plain_text(result.body) == "Choose an answer."


def test_native_item_keeps_unmarked_model_wording_and_recovers_the_omitted_heading():
    heading = _source("body:0001", [("Read this section carefully.", "")])
    heading = replace(
        heading,
        paragraphs=(DocxSourceParagraph(0, heading.text, 2),),
    )
    question = _source("body:0002", [("Answer the question.", "")])
    chunks = (heading, question)
    paths: list[str] = []
    result = aligned_native_item(
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
        foreign_chunks=(),
    ).item
    assert paths == ["rebuilt"]
    assert [paragraph.heading_level for paragraph in result.body] == [2, None]
    assert body_plain_text(result.body) == "Read this section carefully.\nFollow these guidelines."


def _interleaved_matching_row():
    """One physical paragraph whose left and right matching entries alternate."""
    return _source(
        "body:0002",
        [
            ("1. Safety. red", "1. Safety."),
            ("A. Caution. warm", "A. Caution."),
            ("2. blue", "2."),
            ("B. cold", "B."),
        ],
        kind="table",
        separator=" ",
        one_paragraph=True,
    )


def test_interleaved_matching_entries_never_share_one_anothers_source():
    prompt = _source("body:0001", [("Choose an answer.", "")])
    row = _interleaved_matching_row()
    chunks = (prompt, row)
    result = aligned_native_item(
        _item("matching", chunks, match_left=["red", "blue"], match_right=["warm", "cold"]),
        chunks=chunks,
        language="en",
        foreign_chunks=(),
    ).item
    assert [body_plain_text(entry.body) for entry in result.match_left] == [
        "Safety. red",
        "blue",
    ]
    assert [body_plain_text(entry.body) for entry in result.match_right] == [
        "Caution. warm",
        "cold",
    ]
    assert _as_text(result.match_left[0].body[0].segments[0]).marks == ("bold",)
    assert _as_text(result.match_right[0].body[0].segments[0]).marks == ("bold",)


def test_rewritten_matching_entry_rebuilds_only_its_own_span():
    prompt = _source("body:0001", [("Choose an answer.", "")])
    row = _interleaved_matching_row()
    chunks = (prompt, row)
    result = aligned_native_item(
        _item(
            "matching",
            chunks,
            match_left=["red", "blue"],
            match_right=["Caution, warm", "cold"],
        ),
        chunks=chunks,
        language="en",
        foreign_chunks=(),
    ).item
    assert [body_plain_text(entry.body) for entry in result.match_left] == [
        "Safety. red",
        "blue",
    ]
    assert [body_plain_text(entry.body) for entry in result.match_right] == [
        "Caution. warm",
        "cold",
    ]


def test_rewritten_adjacent_choices_keep_their_own_source_spans():
    prompt = _source("body:0001", [("Choose an answer.", "")])
    options = _source(
        "body:0002",
        [
            (
                "A. Identify the important concept. B. blue",
                "A. Identify the important concept. B. blue",
            )
        ],
        one_paragraph=True,
    )
    chunks = (prompt, options)
    result = aligned_native_item(
        _item(
            "single_choice",
            chunks,
            choices=[
                {"text": "Describe the important concept.", "correct": False},
                {"text": "blue", "correct": False},
            ],
        ),
        chunks=chunks,
        language="en",
        foreign_chunks=(),
    ).item
    assert [body_plain_text(choice.body) for choice in result.choices] == [
        "Identify the important concept.",
        "blue",
    ]
    assert _as_text(result.choices[0].body[0].segments[0]).marks == ("bold",)
    assert _as_text(result.choices[1].body[0].segments[0]).marks == ("bold",)


def test_unlabelled_entry_prefix_is_excluded_from_a_rewritten_body():
    prompt = _source("body:0001", [("Choose an answer.", "")])
    options = _source("body:0002", [("Safety. blue", "Safety."), ("red", "")])
    chunks = (prompt, options)
    result = aligned_native_item(
        _item(
            "single_choice",
            chunks,
            body=[
                {
                    "segments": [
                        {
                            "kind": "text",
                            "text": "Safety. Do not mix acids.",
                            "accepted_values": [],
                        }
                    ]
                }
            ],
            choices=[
                {"text": "blue", "correct": False},
                {"text": "red", "correct": False},
            ],
        ),
        chunks=chunks,
        language="en",
        foreign_chunks=(),
    ).item
    assert body_plain_text(result.choices[0].body) == "Safety. blue"
    assert _as_text(result.choices[0].body[0].segments[0]).marks == ("bold",)
    assert body_plain_text(result.choices[1].body) == "red"
    assert body_plain_text(result.body) == "Safety. Do not mix acids."


def test_entry_label_delimiter_never_consumes_a_content_dot():
    prompt = _source("body:0001", [("Choose an answer.", "")])
    options = _source("body:0002", [("A. .NET is useful", "A. .NET"), ("B. plain", "B.")])
    chunks = (prompt, options)
    result = aligned_native_item(
        _item(
            "single_choice",
            chunks,
            choices=[
                {"text": "is useful", "correct": False},
                {"text": "plain", "correct": False},
            ],
        ),
        chunks=chunks,
        language="en",
        foreign_chunks=(),
    ).item
    assert [body_plain_text(choice.body) for choice in result.choices] == [
        ".NET is useful",
        "plain",
    ]
    assert _as_text(result.choices[0].body[0].segments[0]).marks == ("bold",)


def test_duplicate_word_matching_entries_keep_their_own_side_formatting():
    prompt = _source("body:0001", [("Choose an answer.", "")])
    text = "1. red A. red 2. blue B. blue"
    entries = DocxChunk(
        "body:0002",
        "table",
        text,
        text,
        runs=(
            DocxSourceRun(0, "1. ", ("bold",)),
            DocxSourceRun(3, "red", ("bold",)),
            DocxSourceRun(6, " ", ()),
            DocxSourceRun(7, "A. ", ("bold",)),
            DocxSourceRun(10, "red", ("italic",)),
            DocxSourceRun(13, " ", ()),
            DocxSourceRun(14, "2. ", ("bold",)),
            DocxSourceRun(17, "blue", ("bold",)),
            DocxSourceRun(21, " ", ()),
            DocxSourceRun(22, "B. ", ("bold",)),
            DocxSourceRun(25, "blue", ("italic",)),
        ),
        paragraphs=(DocxSourceParagraph(0, text, None),),
    )
    chunks = (prompt, entries)
    result = aligned_native_item(
        _item("matching", chunks, match_left=["red", "blue"], match_right=["red", "blue"]),
        chunks=chunks,
        language="en",
        foreign_chunks=(),
    ).item
    assert [body_plain_text(entry.body) for entry in result.match_left] == ["red", "blue"]
    assert [body_plain_text(entry.body) for entry in result.match_right] == ["red", "blue"]
    assert _as_text(result.match_left[0].body[0].segments[0]).marks == ("bold",)
    assert _as_text(result.match_left[1].body[0].segments[0]).marks == ("bold",)
    assert _as_text(result.match_right[0].body[0].segments[0]).marks == ("italic",)
    assert _as_text(result.match_right[1].body[0].segments[0]).marks == ("italic",)


def test_wholly_rewritten_first_choice_keeps_its_labeled_source_span():
    prompt = _source("body:0001", [("Choose an answer.", "")])
    options = _source(
        "body:0002",
        [("A. Safety. red B. blue", "A. Safety. B.")],
        one_paragraph=True,
    )
    chunks = (prompt, options)
    result = aligned_native_item(
        _item(
            "single_choice",
            chunks,
            choices=[{"text": "Qxz", "correct": False}, {"text": "blue", "correct": False}],
        ),
        chunks=chunks,
        language="en",
        foreign_chunks=(),
    ).item
    assert [body_plain_text(choice.body) for choice in result.choices] == ["Safety. red", "blue"]
    assert _as_text(result.choices[0].body[0].segments[0]).marks == ("bold",)
    assert _as_text(result.choices[1].body[0].segments[0]).marks == ()
