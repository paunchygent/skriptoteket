"""Unit coverage for class-list parsing heuristics.

Purpose:
  Pin the pure parsing rules for text and row-based roster inputs.

Relationships:
  - Exercises `ClassListHeuristicParser`.
  - Complements handler-level example corpus tests.
"""

from __future__ import annotations

from skriptoteket.domain.curated_apps.classroom_planner.import_heuristics import (
    ClassListHeuristicParser,
)


def test_parse_simple_text() -> None:
    parser = ClassListHeuristicParser()
    text = "1. Alice Andersson\n2. Bob Berglund\n3. Charlie Ceder"
    preview = parser.parse(file_name="test.txt", text=text, rows=None)

    assert preview.file_name == "test.txt"
    assert len(preview.parsed_students) == 3
    assert preview.parsed_students[0].full_name == "Alice Andersson"
    assert preview.parsed_students[1].full_name == "Bob Berglund"
    assert preview.parsed_students[2].full_name == "Charlie Ceder"


def test_parse_comma_separated_text() -> None:
    parser = ClassListHeuristicParser()
    text = "Andersson, Alice\nBerglund, Bob\nCeder, Charlie"
    preview = parser.parse(file_name="test.txt", text=text, rows=None)

    assert len(preview.parsed_students) == 3
    assert preview.parsed_students[0].full_name == "Alice Andersson"
    assert preview.parsed_students[0].family_name == "Andersson"
    assert preview.parsed_students[0].given_name == "Alice"


def test_detect_class_name_from_text() -> None:
    parser = ClassListHeuristicParser()
    text = "Klasslista för SA24D\n\n1. Alice Andersson"
    preview = parser.parse(file_name="roster.txt", text=text, rows=None)

    assert preview.suggested_class_name == "SA24D"


def test_parse_rows_xlsx_style() -> None:
    parser = ClassListHeuristicParser()
    rows = [
        ["Nr", "Namn", "Klass"],
        ["1", "Alice Andersson", "SA24D"],
        ["2", "Bob Berglund", "SA24D"],
    ]
    preview = parser.parse(file_name="test.xlsx", text=None, rows=rows)

    assert preview.suggested_class_name == "SA24D"
    assert len(preview.parsed_students) == 2
    assert preview.parsed_students[0].full_name == "Alice Andersson"
    assert preview.parsed_students[0].row_number == 1


def test_accumulate_from_multiple_variants() -> None:
    parser = ClassListHeuristicParser()
    # Mock behavior where we have both rows and text (e.g. from a PDF where we tried both)
    rows = [["1", "Alice Andersson"]]
    text = "1 Alice Andersson\n2 Bob Berglund"

    preview = parser.parse(file_name="test.pdf", text=text, rows=rows)

    # Should merge Alice and add Bob
    assert len(preview.parsed_students) == 2
    names = {s.full_name for s in preview.parsed_students}
    assert "Alice Andersson" in names
    assert "Bob Berglund" in names


def test_parse_rows_without_numeric_index() -> None:
    parser = ClassListHeuristicParser()
    rows = [
        ["Andersson", "Alice"],
        ["Berglund", "Bob"],
    ]

    preview = parser.parse(file_name="test.csv", text=None, rows=rows)

    assert preview.suggested_class_name is None
    assert len(preview.parsed_students) == 2
    assert preview.parsed_students[0].full_name == "Alice Andersson"
    assert preview.parsed_students[1].full_name == "Bob Berglund"


def test_parse_rows_without_numeric_index_preserves_given_name_first_order() -> None:
    parser = ClassListHeuristicParser()
    rows = [
        ["Alice", "Andersson"],
        ["Bob", "Berglund"],
    ]

    preview = parser.parse(file_name="test.tsv", text=None, rows=rows)

    assert preview.suggested_class_name is None
    assert len(preview.parsed_students) == 2
    assert preview.parsed_students[0].full_name == "Alice Andersson"
    assert preview.parsed_students[1].full_name == "Bob Berglund"


def test_parse_indexed_split_name_rows_skips_headers_and_orders_names() -> None:
    parser = ClassListHeuristicParser()
    rows = [
        ["Nr", "Efternamn", "Förnamn"],
        ["1", "Andersson", "Alice"],
        ["2", "Berglund", "Bob"],
    ]

    preview = parser.parse(file_name="test.xlsx", text=None, rows=rows)

    assert preview.suggested_class_name is None
    assert [student.full_name for student in preview.parsed_students] == [
        "Alice Andersson",
        "Bob Berglund",
    ]
