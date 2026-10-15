"""The producer's tiers, A10 bound, real-word protection and determinism.

The committed misspelling_data package is delivered by its own build; these
tests inject cached fixture data through the loader seam until it lands, then
also prove the shipped data through the same producer.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from skriptoteket.domain.curated_apps.exam_workspace import answer_misspellings
from skriptoteket.domain.curated_apps.exam_workspace.answer_misspellings import (
    _rep_candidates,
    produce_answer_misspellings,
)
from skriptoteket.domain.curated_apps.exam_workspace.answer_spelling import (
    is_allowed_answer_spelling_variant,
)
from skriptoteket.domain.curated_apps.exam_workspace.exam_document_language import Language


@dataclass(frozen=True)
class _FixtureData:
    attested: dict[str, tuple[str, ...]] = field(default_factory=dict)
    rep: tuple[tuple[str, str], ...] = ()
    keyboard: dict[str, tuple[str, ...]] = field(default_factory=dict)
    valid_words: frozenset[str] = frozenset()


def _install(monkeypatch: pytest.MonkeyPatch, fixtures: dict[str, _FixtureData]) -> None:
    monkeypatch.setattr(
        answer_misspellings, "load_misspelling_data", lambda language: fixtures[language]
    )


def test_candidates_follow_tier_order(monkeypatch: pytest.MonkeyPatch) -> None:
    _install(
        monkeypatch,
        {
            "sv": _FixtureData(
                attested={"kattr": ("kattrx",)},
                rep=(("w", "r"),),
                keyboard={"a": ("s",), "r": ("e",)},
            )
        },
    )

    result = produce_answer_misspellings(("kattr",), language="sv")

    assert result == ("kattrx", "kattw", "ksttr")


def test_attested_order_is_stable_and_capped_at_three(monkeypatch: pytest.MonkeyPatch) -> None:
    _install(
        monkeypatch,
        {
            "sv": _FixtureData(
                attested={"kattr": ("kattrx", "katty", "kattz", "kattq")},
            )
        },
    )

    result = produce_answer_misspellings(("kattr",), language="sv")

    assert result == ("kattrx", "katty", "kattz")


def test_attested_inflected_word_is_dropped(monkeypatch: pytest.MonkeyPatch) -> None:
    _install(
        monkeypatch,
        {
            "sv": _FixtureData(
                attested={"katt": ("katts", "kattx")},
                valid_words=frozenset({"katts"}),
            )
        },
    )

    result = produce_answer_misspellings(("katt",), language="sv")

    assert result == ("kattx",)


def test_rep_real_word_falls_through_to_the_next_occurrence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install(
        monkeypatch,
        {
            "sv": _FixtureData(
                rep=(("x", "t"),),
                valid_words=frozenset({"kaxt"}),
            )
        },
    )

    result = produce_answer_misspellings(("katt",), language="sv")

    assert result == ("katx",)


def test_keyboard_real_word_falls_through_to_the_next_neighbour(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install(
        monkeypatch,
        {
            "sv": _FixtureData(
                keyboard={"t": ("r", "s")},
                valid_words=frozenset({"kart"}),
            )
        },
    )

    result = produce_answer_misspellings(("katt",), language="sv")

    assert result == ("kast", "katr", "kats")


def test_multiword_changed_token_that_is_a_real_word_is_dropped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install(
        monkeypatch,
        {
            "en": _FixtureData(
                attested={"the cat": ("the car", "the kat")},
                valid_words=frozenset({"car"}),
            )
        },
    )

    result = produce_answer_misspellings(("the cat",), language="en")

    assert result == ("the kat",)


@pytest.mark.parametrize(
    ("accepted", "candidate", "real_word"),
    [("some thing", "something", "something"), ("the cat,", "the car,", "car")],
)
def test_spacing_or_punctuation_never_hides_a_real_word(
    monkeypatch: pytest.MonkeyPatch, accepted: str, candidate: str, real_word: str
) -> None:
    _install(
        monkeypatch,
        {"en": _FixtureData(attested={accepted: (candidate,)}, valid_words=frozenset({real_word}))},
    )
    assert produce_answer_misspellings((accepted,), language="en") == ()


def test_compound_spacing_variant_stays_eligible(monkeypatch: pytest.MonkeyPatch) -> None:
    _install(
        monkeypatch,
        {
            "sv": _FixtureData(
                attested={"tillslut": ("till slut",)},
                valid_words=frozenset({"till", "slut"}),
            )
        },
    )

    result = produce_answer_misspellings(("tillslut",), language="sv")

    assert result == ("till slut",)


def test_all_token_phrase_of_real_words_is_dropped(monkeypatch: pytest.MonkeyPatch) -> None:
    _install(
        monkeypatch,
        {
            "sv": _FixtureData(
                attested={"arbetsbok": ("arbete bok", "arbetsbock")},
                valid_words=frozenset({"arbete", "bok"}),
            )
        },
    )

    result = produce_answer_misspellings(("arbetsbok",), language="sv")

    assert result == ("arbetsbock",)


def test_other_gold_answers_are_never_emitted(monkeypatch: pytest.MonkeyPatch) -> None:
    _install(
        monkeypatch,
        {"sv": _FixtureData(attested={"katt": ("kattx",)})},
    )

    result = produce_answer_misspellings(("katt",), language="sv", other_gold_answers=("kattx",))

    assert result == ()


def test_far_candidates_fail_the_a10_bound(monkeypatch: pytest.MonkeyPatch) -> None:
    _install(
        monkeypatch,
        {"sv": _FixtureData(attested={"katt": ("hundra",)})},
    )

    assert produce_answer_misspellings(("katt",), language="sv") == ()


def test_rep_anchors_match_word_edges_and_whole_word() -> None:
    rules = (("q", "^k"), ("z", "t$"), ("!", "^katt$"))

    assert _rep_candidates("katt", rules) == ["qatt", "katz", "!"]


def test_rep_candidates_keep_table_then_occurrence_order() -> None:
    rules = (("z", "t"), ("x", "k"))

    assert _rep_candidates("katt", rules) == ["kazt", "katz", "xatt"]


def test_rep_anchored_pattern_never_matches_mid_word() -> None:
    assert _rep_candidates("skatt", (("q", "^k"),)) == []
    assert _rep_candidates("katta", (("z", "tt$"),)) == []
    assert _rep_candidates("skatt", (("q", "^katt$"),)) == []


def test_rep_whitespace_dot_and_underscore_rules_are_skipped() -> None:
    rules = (("q", "k t"), ("z", "k."), ("w", "k_att"), ("^bla$", "bl.a."))

    assert _rep_candidates("katt", rules) == []


def test_each_accepted_value_keeps_its_own_three(monkeypatch: pytest.MonkeyPatch) -> None:
    _install(
        monkeypatch,
        {
            "sv": _FixtureData(
                attested={
                    "katt": ("kattx", "katty", "kattz", "kattq"),
                    "kattr": ("kattrx", "kattry"),
                }
            )
        },
    )

    result = produce_answer_misspellings(("katt", "kattr"), language="sv")

    assert result == ("kattx", "katty", "kattz", "kattrx", "kattry")


def test_poisoned_rep_rules_never_apply(monkeypatch: pytest.MonkeyPatch) -> None:
    _install(
        monkeypatch,
        {
            "sv": _FixtureData(
                rep=((".", "t"), (" ", "t"), ("^", "t"), ("x", "t")),
            )
        },
    )

    result = produce_answer_misspellings(("katt",), language="sv")

    assert result == ("kaxt", "katx")


def test_english_language_uses_the_same_tiers(monkeypatch: pytest.MonkeyPatch) -> None:
    _install(
        monkeypatch,
        {
            "en": _FixtureData(
                attested={"believe": ("belief", "beleave")},
                rep=(("ei", "ie"),),
                keyboard={"v": ("b",)},
                valid_words=frozenset({"belief"}),
            )
        },
    )

    result = produce_answer_misspellings(("believe",), language="en")

    assert result == ("beleave", "beleive", "beliebe")


def test_output_is_deterministic_and_keeps_accepted_order(monkeypatch: pytest.MonkeyPatch) -> None:
    _install(
        monkeypatch,
        {
            "sv": _FixtureData(
                attested={"beta": ("betax",), "alpha": ("alphax",)},
            )
        },
    )

    first = produce_answer_misspellings(("beta", "alpha"), language="sv")
    second = produce_answer_misspellings(("beta", "alpha"), language="sv")

    assert first == ("betax", "alphax")
    assert first == second


_DATA_ROOT = Path(answer_misspellings.__file__).with_name("misspelling_data")


@pytest.mark.parametrize("language", ["sv", "en"])
def test_shipped_data_survives_the_producer(language: Language) -> None:
    from skriptoteket.domain.curated_apps.exam_workspace.misspelling_data import (
        load_misspelling_data,
    )

    data = load_misspelling_data(language)
    payload = json.loads((_DATA_ROOT / f"{language}.json").read_text(encoding="utf-8"))
    produced = False
    for correct in list(payload["attested"])[:20]:
        result = produce_answer_misspellings((correct,), language=language)
        assert result == produce_answer_misspellings((correct,), language=language)
        for value in result:
            assert is_allowed_answer_spelling_variant(correct, value)
            assert value not in data.valid_words
        produced = produced or bool(result)
    assert produced
