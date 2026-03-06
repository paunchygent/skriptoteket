"""Unit tests for LanguageTool-assisted textbook diacritics proposal generation."""

from __future__ import annotations

from dataclasses import dataclass

from scripts.build_textbook_corpus_diacritics_assist import (
    LanguageToolMatch,
    _allow_candidate,
    _build_chunks,
    _is_strict_diacritic_only_change,
    _patch_payload,
    _select_diacritic_replacement,
    suggest_diacritics_patches,
)


@dataclass(frozen=True, slots=True)
class _FakeChecker:
    """Deterministic checker stub used for pure unit tests."""

    def check(self, *, text: str, language: str) -> list[LanguageToolMatch]:
        matches: list[LanguageToolMatch] = []
        if "forhoppning" in text:
            matches.append(
                LanguageToolMatch(
                    offset=text.index("forhoppning"),
                    length=len("forhoppning"),
                    replacements=("förhoppning", "inhoppning"),
                    rule_id="HUNSPELL_RULE",
                    message="stavfel",
                )
            )
        if "varfor" in text:
            matches.append(
                LanguageToolMatch(
                    offset=text.index("varfor"),
                    length=len("varfor"),
                    replacements=("varför", "varor"),
                    rule_id="HUNSPELL_RULE",
                    message="stavfel",
                )
            )
        return matches

    @property
    def service_name(self) -> str:
        return "fake"

    @property
    def base_url(self) -> str:
        return "http://fake"


def test_select_diacritic_replacement_returns_single_safe_candidate() -> None:
    value = _select_diacritic_replacement(
        original="forhoppning",
        replacements=("förhoppning", "inhoppning"),
    )
    assert value == "förhoppning"


def test_select_diacritic_replacement_rejects_ambiguous_candidates() -> None:
    value = _select_diacritic_replacement(
        original="har",
        replacements=("här", "hår"),
    )
    assert value is None


def test_strict_diacritic_change_rejects_non_diacritic_mutation() -> None:
    assert _is_strict_diacritic_only_change(original="for", replacement="för")
    assert not _is_strict_diacritic_only_change(original="NaN", replacement="Nån")


def test_allow_candidate_rejects_chemistry_sensitive_tokens() -> None:
    assert not _allow_candidate(original="Ag", replacement="Äg", line_text="Ag + Cl- -> AgCl")
    assert not _allow_candidate(original="NaN", replacement="Nån", line_text="n(NaN) = 0,5 mol")
    assert _allow_candidate(
        original="forsta",
        replacement="första",
        line_text="Det ar min forsta rad.",
    )


def test_build_chunks_splits_at_max_chars_boundary() -> None:
    chunks = _build_chunks(lines=["aaaa", "bbbb", "cccc"], max_chars=9)
    assert len(chunks) == 2
    assert chunks[0].text == "aaaa\nbbbb"
    assert chunks[1].text == "cccc"


def test_suggest_diacritics_patches_emits_line_replacements() -> None:
    text = "Det ar en forhoppning.\nVi undrar varfor detta ar sant."
    suggestions, requests_made, failed_chunks = suggest_diacritics_patches(
        markdown_text=text,
        language="sv-SE",
        checker=_FakeChecker(),
        chunk_max_chars=200,
        max_requests_per_second=0,
        max_suggestions=0,
        max_retries=1,
        retry_backoff_s=0,
    )

    assert requests_made == 1
    assert failed_chunks == 0
    assert len(suggestions) == 2

    first = suggestions[0]
    second = suggestions[1]
    assert first.line_no == 1
    assert second.line_no == 2
    assert first.replacement_line == "Det ar en förhoppning."
    assert second.replacement_line == "Vi undrar varför detta ar sant."

    payload = _patch_payload(
        suggestion=first,
        service_name="fake",
        service_base_url="http://fake",
        language="sv-SE",
    )
    assert payload["status"] == "proposed"
    assert payload["source"]["line_no"] == 1
    assert payload["change"]["replacement"] == "Det ar en förhoppning."
