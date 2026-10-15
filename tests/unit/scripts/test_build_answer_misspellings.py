"""Offline source extraction, inflection expansion and deterministic ranking."""

from pathlib import Path

import pytest

from scripts.build_answer_misspellings import rank_attested
from scripts.build_answer_misspellings_hunspell import expand_word_forms, parse_rep_rules
from scripts.build_answer_misspellings_sources import (
    KEYBOARD_LAYOUTS,
    AttestedPair,
    filter_rep_rules,
    keyboard_neighbours,
    parse_awb_pairs,
    parse_birkbeck_pairs,
    parse_for_machines_pairs,
    parse_lovs_pairs,
)


def test_source_tier_precedes_frequency_and_lexical_breaks_ties() -> None:
    pairs = [
        AttestedPair("business", "bussiness", 5),
        *[AttestedPair("business", "busness", 2)] * 10,
        AttestedPair("business", "buisness", 5),
    ]
    ranked, stats = rank_attested(pairs, set())
    assert ranked == {"business": ["buisness", "bussiness", "busness"]}
    assert stats["attested_pairs"] == 3
    pairs.append(AttestedPair("business", "bussiness", 5))
    assert rank_attested(pairs, set())[0]["business"][0] == "bussiness"


def test_build_rejects_real_inflections_and_out_of_bound_pairs() -> None:
    pairs = [
        AttestedPair("walk", "walks", 5),
        AttestedPair("walk", "wolk", 5),
        AttestedPair("walk", "walking", 5),
    ]
    ranked, stats = rank_attested(pairs, {"walk", "walks"})
    assert ranked == {"walk": ["wolk"]}
    assert stats["real_word_rows_dropped"] == 1
    assert stats["a10_rows_dropped"] == 1


def test_inflection_expansion_includes_suffixes_and_cross_product(tmp_path: Path) -> None:
    affix = tmp_path / "test.aff"
    dictionary = tmp_path / "test.dic"
    affix.write_text("SET UTF-8\nPFX U Y 1\nPFX U 0 un .\nSFX S Y 1\nSFX S 0 s .\n")
    dictionary.write_text("2\ncat/S\nknown/US\n")
    assert expand_word_forms(dictionary, affix) == {
        "cat",
        "cats",
        "known",
        "knowns",
        "unknown",
        "unknowns",
    }


@pytest.mark.parametrize(
    ("mode", "suffix", "needs_affix"), [("long", "AA", "BB"), ("num", "1", "2")]
)
def test_continuation_flags_use_the_declared_encoding(
    tmp_path: Path, mode: str, suffix: str, needs_affix: str
) -> None:
    affix = tmp_path / "test.aff"
    dictionary = tmp_path / "test.dic"
    affix.write_text(
        f"SET UTF-8\nFLAG {mode}\nNEEDAFFIX {needs_affix}\n"
        f"SFX {suffix} Y 1\nSFX {suffix} 0 s/{needs_affix} .\n"
    )
    dictionary.write_text(f"1\ncat/{suffix}\n")
    assert expand_word_forms(dictionary, affix) == {"cat"}


def test_rep_columns_are_not_double_inverted_and_anchors_survive(tmp_path: Path) -> None:
    path = tmp_path / "test.aff"
    path.write_text("REP 4\nREP shun tion\nREP ^teh$ ^the$\nREP a_lot alot\nREP b.a ba\n")
    assert filter_rep_rules(parse_rep_rules(path)) == (("shun", "tion"), ("^teh$", "^the$"))


def test_keyboard_has_horizontal_neighbours_and_language_owned_keys() -> None:
    sv = keyboard_neighbours(KEYBOARD_LAYOUTS["sv"])
    en = keyboard_neighbours(KEYBOARD_LAYOUTS["en"])
    assert "w" in sv["q"] and "q" in sv["w"]
    assert "p" in sv["å"] and "å" in sv["p"]
    assert "å" not in en
    assert "å" not in en["p"]
    assert all(key in sv[neighbour] for key, neighbours in sv.items() for neighbour in neighbours)


def test_editor_sources_parse_pairs_but_exclude_awb_cartesian_combinations() -> None:
    lovs = "== Stavfel ==\n=== Vanliga stavfel ===\n|-\n| adresss || adress || note\n|-\n"
    assert parse_lovs_pairs(lovs) == [AttestedPair("adress", "adresss", 2)]
    suffixes = "== Stavfel ==\n|-\n| aborre, -n -ar, abbore || abborre || note\n|-\n"
    assert parse_lovs_pairs(suffixes) == [
        AttestedPair("abborre", "aborre", 2),
        AttestedPair("abborre", "abbore", 2),
    ]
    awb = (
        '<Typo word="adress" find="\\badresss\\b" replace="adress" />\n'
        '<Typo word="adress" find="\\b(adresss|adrees)\\b" replace="adress" />\n'
        '<Typo word="complex" find="(a|b)(c|d)" replace="$1$2" />'
    )
    assert parse_awb_pairs(awb) == [
        AttestedPair("adress", "adresss", 1),
        AttestedPair("adress", "adresss", 1),
        AttestedPair("adress", "adrees", 1),
    ]
    assert parse_birkbeck_pairs("$receive\nrecieve\n") == [AttestedPair("receive", "recieve", 5)]
    assert parse_for_machines_pairs(" recieve->receive\n") == [
        AttestedPair("receive", "recieve", 2)
    ]
