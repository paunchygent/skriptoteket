"""The committed inflected-word guard and all static attested pairs."""

from concurrent.futures import ThreadPoolExecutor

import pytest

from skriptoteket.domain.curated_apps.exam_workspace import misspelling_data as data
from skriptoteket.domain.curated_apps.exam_workspace.answer_spelling import (
    is_allowed_answer_spelling_variant,
)
from skriptoteket.domain.curated_apps.exam_workspace.exam_document_language import Language


@pytest.mark.parametrize("language", ["sv", "en"])
def test_every_committed_pair_is_bounded_and_excludes_inflected_real_words(
    language: Language,
) -> None:
    loaded = data.load_misspelling_data(language)
    assert loaded.attested
    for correct, misspellings in loaded.attested.items():
        assert misspellings
        for miss in misspellings:
            assert miss not in loaded.valid_words, (correct, miss)
            assert is_allowed_answer_spelling_variant(correct, miss), (correct, miss)


@pytest.mark.parametrize(
    ("language", "forms"),
    [
        ("sv", ("eleverna", "katternas", "husens", "skapad", "springer")),
        ("en", ("cats", "walked", "walks", "running", "children")),
    ],
)
def test_real_inflections_not_just_stems_are_present(
    language: Language, forms: tuple[str, ...]
) -> None:
    words = data.load_misspelling_data(language).valid_words
    assert all(form in words for form in forms)


def test_simultaneous_first_requests_load_the_static_payload_only_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data._load_language_data.cache_clear()
    original = data._decode_lexicon
    decodes: list[int] = []

    def decode(payload: bytes) -> data.WordFormLexicon:
        decodes.append(len(payload))
        return original(payload)

    monkeypatch.setattr(data, "_decode_lexicon", decode)
    languages: list[Language] = ["sv"] * 8
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(data.load_misspelling_data, languages))
    assert len(decodes) == 1
    assert all(result is results[0] for result in results)
