"""A marked continuation paragraph belongs to the entry it follows.

A continuation heading after a choice, a marked continuation after the last choice, and
a marked continuation after the last matching entry each join that entry's body; the
entry's own source span owns the continuation, never a neighboring entry.
"""

from dataclasses import replace

import pytest

from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_build import aligned_native_item
from skriptoteket.domain.curated_apps.exam_workspace.shared_body import body_plain_text
from tests.unit.domain.curated_apps.exam_workspace.native_entry_formatting_test_support import (
    _as_text,
    _item,
    _source,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("continuation_label", ["Follow the safety note.", ""])
def test_continuation_heading_paragraph_belongs_to_its_entry(continuation_label):
    prompt = _source("body:0001", [("Choose an answer.", "")])
    options = _source(
        "body:0002",
        [
            ("A. red", "A."),
            ("Follow the safety note.", continuation_label),
            ("B. blue", "B."),
        ],
    )
    options = replace(
        options,
        paragraphs=(
            options.paragraphs[0],
            replace(options.paragraphs[1], heading_level=2),
            options.paragraphs[2],
        ),
    )
    chunks = (prompt, options)
    result = aligned_native_item(
        _item(
            "single_choice",
            chunks,
            choices=[{"text": "red", "correct": False}, {"text": "blue", "correct": False}],
        ),
        chunks=chunks,
        language="en",
        foreign_chunks=(),
    ).item
    assert [body_plain_text(choice.body) for choice in result.choices] == [
        "red\nFollow the safety note.",
        "blue",
    ]
    assert result.choices[0].body[1].heading_level == 2
    assert _as_text(result.choices[0].body[1].segments[0]).marks == (
        ("bold",) if continuation_label else ()
    )


def test_marked_continuation_after_the_last_choice_belongs_to_that_choice():
    prompt = _source("body:0001", [("Choose an answer.", "")])
    options = _source(
        "body:0002",
        [
            ("A. red", "A."),
            ("B. blue", "B."),
            ("Follow the safety note.", "Follow the safety note."),
        ],
    )
    chunks = (prompt, options)
    result = aligned_native_item(
        _item(
            "single_choice",
            chunks,
            choices=[{"text": "red", "correct": False}, {"text": "blue", "correct": False}],
        ),
        chunks=chunks,
        language="en",
        foreign_chunks=(),
    ).item
    assert [body_plain_text(choice.body) for choice in result.choices] == [
        "red",
        "blue\nFollow the safety note.",
    ]
    assert _as_text(result.choices[1].body[1].segments[0]).marks == ("bold",)


def test_marked_continuation_after_the_last_matching_entry_belongs_to_it():
    prompt = _source("body:0001", [("Choose an answer.", "")])
    entries = _source(
        "body:0002",
        [
            ("1. red", "1."),
            ("A. warm", "A."),
            ("2. blue", "2."),
            ("B. cold", "B."),
            ("Follow the safety note.", "Follow the safety note."),
        ],
        kind="table",
    )
    chunks = (prompt, entries)
    result = aligned_native_item(
        _item("matching", chunks, match_left=["red", "blue"], match_right=["warm", "cold"]),
        chunks=chunks,
        language="en",
        foreign_chunks=(),
    ).item
    assert [body_plain_text(entry.body) for entry in result.match_left] == ["red", "blue"]
    assert [body_plain_text(entry.body) for entry in result.match_right] == [
        "warm",
        "cold\nFollow the safety note.",
    ]
    assert _as_text(result.match_right[1].body[1].segments[0]).marks == ("bold",)
