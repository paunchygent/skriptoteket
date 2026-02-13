from __future__ import annotations

from skriptoteket.infrastructure.curated_apps.apps.reagent_prep_chef.sds_parsers import (
    extract_hazard_codes_from_text,
    extract_pictograms_from_text,
    extract_pubchem_ghs,
    extract_pubchem_nonhazardous,
    extract_signal_word_from_text,
    is_nonhazardous_from_text,
    parse_sds_heuristics_from_text,
)


def test_extract_pubchem_ghs_reads_hazard_codes_and_signal() -> None:
    pug_view = {
        "Record": {
            "Section": [
                {
                    "TOCHeading": "Safety and Hazards",
                    "Section": [
                        {
                            "TOCHeading": "GHS Classification",
                            "Information": [
                                {
                                    "Name": "GHS Hazard Statements",
                                    "Value": {
                                        "StringWithMarkup": [
                                            {"String": "H314 Causes severe skin burns."},
                                            {"String": "H318 Causes serious eye damage."},
                                        ]
                                    },
                                },
                                {
                                    "Name": "Pictogram(s)",
                                    "Value": {
                                        "StringWithMarkup": [
                                            {"Markup": [{"URL": "https://example.com/GHS05.svg"}]}
                                        ]
                                    },
                                },
                                {
                                    "Name": "Signal",
                                    "Value": {"StringWithMarkup": [{"String": "Danger"}]},
                                },
                            ],
                        }
                    ],
                }
            ]
        }
    }

    hazard_codes, pictograms, signal_word = extract_pubchem_ghs(pug_view)

    assert hazard_codes == ["H314", "H318"]
    assert pictograms == ["GHS05"]
    assert signal_word == "danger"


def test_extract_pubchem_nonhazardous_detects_not_classified() -> None:
    pug_view = {
        "Record": {
            "Section": [
                {
                    "TOCHeading": "Safety and Hazards",
                    "Section": [
                        {
                            "TOCHeading": "GHS Classification",
                            "Information": [
                                {
                                    "Name": "GHS Classification",
                                    "Value": {
                                        "StringWithMarkup": [
                                            {"String": "Not classified as hazardous."}
                                        ]
                                    },
                                }
                            ],
                        }
                    ],
                }
            ]
        }
    }
    assert extract_pubchem_nonhazardous(pug_view) is True


def test_extract_sds_text_helpers_parse_expected_values() -> None:
    text = """
    Section 10 Stability and Reactivity
    Incompatible materials: Acids, strong oxidizers
    Hazardous reactions: Violently exothermic reaction
    Signal word: Warning
    GHS05
    H314 H318
    """

    incompatibilities, exothermicity, reaction_notes = parse_sds_heuristics_from_text(text)
    assert incompatibilities == ["Acids, strong oxidizers"]
    assert exothermicity in {"medium", "high"}
    assert reaction_notes == ["Violently exothermic reaction"]

    assert extract_hazard_codes_from_text(text) == ["H314", "H318"]
    assert extract_pictograms_from_text(text) == ["GHS05"]
    assert extract_signal_word_from_text(text) == "warning"


def test_extract_hazard_codes_handles_spacing_and_dashes() -> None:
    text = "H 319 H-315 H314 H- 318"
    assert extract_hazard_codes_from_text(text) == ["H314", "H315", "H318", "H319"]


def test_is_nonhazardous_from_text_detects_not_classified() -> None:
    text = "Not classified as hazardous according to CLP."
    assert is_nonhazardous_from_text(text) is True


def test_parse_sds_heuristics_filters_boilerplate_placeholders() -> None:
    text = """
    Section 10 Stability and Reactivity
    Incompatible materials: with which the chemical could react to produce a hazardous situation.
    Hazardous reactions: will react or polymerize, which could release excess pressure or heat.
    Conditions to avoid: static discharge, shock, vibrations,
    or because of use, storage, or heating.
    """
    incompatibilities, exothermicity, reaction_notes = parse_sds_heuristics_from_text(text)
    assert incompatibilities == []
    assert reaction_notes == []
    assert exothermicity is None


def test_parse_sds_heuristics_requires_section_10() -> None:
    text = """
    Safety Data Sheet
    Incompatible materials: Acids
    """
    incompatibilities, exothermicity, reaction_notes = parse_sds_heuristics_from_text(text)
    assert incompatibilities == []
    assert reaction_notes == []
    assert exothermicity is None
