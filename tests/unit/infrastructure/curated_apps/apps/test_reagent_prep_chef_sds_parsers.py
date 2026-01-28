from __future__ import annotations

from skriptoteket.infrastructure.curated_apps.apps.reagent_prep_chef.sds_parsers import (
    extract_hazard_codes_from_text,
    extract_pictograms_from_text,
    extract_pubchem_ghs,
    extract_signal_word_from_text,
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
