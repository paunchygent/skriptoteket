"""Unit tests for deterministic mechanical textbook markdown cleanup."""

from __future__ import annotations

from scripts.build_textbook_corpus_mechanical_cleanup import cleanup_textbook_markdown


def test_cleanup_inserts_page_anchor_outside_protected_zone() -> None:
    text = "\n".join(
        [
            "## Innehall",
            "",
            "12",
            "",
            "## 1 Den gudomliga konsten",
            "Text",
            "",
        ]
    )

    result = cleanup_textbook_markdown(text=text, max_line_length=350)

    assert "[[page:12]]" in result.cleaned_markdown
    assert any(event.code == "page_anchor_inserted" for event in result.transforms)


def test_cleanup_does_not_autofix_page_anchor_in_protected_zone() -> None:
    text = "\n".join(
        [
            "## SVAR OCH LOSNInGAR",
            "",
            "101",
            "",
            "Svarstext",
            "",
        ]
    )

    result = cleanup_textbook_markdown(text=text, max_line_length=350)

    assert "[[page:101]]" not in result.cleaned_markdown
    assert any(
        issue.code == "protected_zone_page_anchor_candidate" and issue.manual_required
        for issue in result.issues
    )


def test_cleanup_emits_long_line_manual_issue() -> None:
    long_line = "A" * 500
    text = "\n".join(["## Section", long_line, ""])

    result = cleanup_textbook_markdown(text=text, max_line_length=350)

    assert any(
        issue.code == "long_line_extreme" and issue.manual_required for issue in result.issues
    )


def test_cleanup_is_deterministic() -> None:
    text = "\n".join(
        [
            "## Innehall\t",
            "",
            "",
            "",
            "17",
            "",
            "## Kapitel 2....",
            "<!-- image -->",
            "",
        ]
    )

    result_one = cleanup_textbook_markdown(text=text, max_line_length=350)
    result_two = cleanup_textbook_markdown(text=text, max_line_length=350)

    assert result_one.cleaned_markdown == result_two.cleaned_markdown
    assert result_one.transforms == result_two.transforms
    assert result_one.issues == result_two.issues
