"""Unit tests for SDS shortcard extraction and validation invariants."""

from __future__ import annotations

from scripts.build_reagent_prep_chef_sds_shortcards import (
    _build_manual_checklist,
    _extract_shortcard,
    _validate_markdown_structure,
)


def test_extract_shortcard_parses_identity_and_clp_fields() -> None:
    markdown_text = """
## Säkerhetsdatablad
## Natriumvätesulfat ≥93 %, pärlform
produktnummer:
2373
Version:
4.0 sv
Omarbetning: 18.09.2024
## AVSNITT 1: Namnet på ämnet/blandningen och bolaget/företaget
Namnet på ämnet
Natriumvätesulfat
CAS nummer
7681-38-1
EG-nummer
231-665-7
Registeringsnummer (REACH)
01-2119552465-36-xxxx
Indexnummer i bilaga VI till CLP
016-046-00-X
## AVSNITT 2: Farliga egenskaper
Klassificering enligt förordning (EG) nr 1272/2008 (CLP)
Eye Dam. 1
Signalord
Fara
H318 Orsakar allvarliga ögonskador.
P280
P305+P351+P338
P310
GHS05
## AVSNITT 8: Begränsning av exponeringen/personligt skydd
Använd korgglasögon med sidoskydd.
Handskar av butylgummi (0,5 mm, 480 min).
Vid dammbildning använd partikelfilter (P1).
## AVSNITT 6: Åtgärder vid oavsiktliga utsläpp
Tas upp mekaniskt. Begränsa damm. Ventilera.
## AVSNITT 10: Stabilitet och reaktivitet
Våldsam reaktion med stark alkali och starkt oxiderande ämnen.
## AVSNITT 13: Avfallshantering
Hanteras som farligt avfall. Töm ej i avloppet.
""".strip()

    shortcard, issues = _extract_shortcard(
        sds_ref="NaHSO4",
        provider="carlroth",
        md_file_name="NaHSO4__carlroth__undated.md",
        markdown_text=markdown_text,
        display_name="Natriumvätesulfat (NaHSO4)",
        ppe_default=["Skyddsglasögon"],
    )

    assert issues == []
    assert shortcard.name_sv == "Natriumvätesulfat"
    assert shortcard.formula == "NaHSO4"
    assert shortcard.product_no == "2373"
    assert shortcard.cas == "7681-38-1"
    assert shortcard.eg == "231-665-7"
    assert shortcard.reach_registration == "01-2119552465-36-xxxx"
    assert shortcard.clp_index == "016-046-00-X"
    assert shortcard.version == "4.0 sv"
    assert shortcard.revision_date == "2024-09-18"
    assert shortcard.clp["h_codes"] == ["H318"]
    assert shortcard.clp["signal_word"] == "Fara"
    assert "GHS05" in shortcard.clp["pictograms"]
    assert shortcard.ppe_notes["eyes"] is not None
    assert shortcard.spill_notes is not None
    assert shortcard.waste_notes is not None
    assert shortcard.parser_ground_truth is False


def test_validate_markdown_structure_reports_artifacts_and_missing_section_1() -> None:
    markdown_text = """
Sida: 1 av 8
## Säkerhetsdatablad
<!-- image -->
## AVSNITT 2: Farliga egenskaper
""".strip()

    issues = _validate_markdown_structure(markdown_text)
    codes = {issue.code for issue in issues}

    assert "structure_missing_h2_start" in codes
    assert "structure_missing_section_1" in codes
    assert "structure_contains_html_comment" in codes


def test_manual_checklist_is_global_when_any_issue_exists() -> None:
    checklist = _build_manual_checklist(
        markdown_file_names=["A.md", "B.md", "C.md"],
        issue_counts_by_code={"structure_missing_section_1": 2},
    )

    assert "manually validate **all** SDS markdown files" in checklist
    assert "- [ ] `A.md`" in checklist
    assert "- [ ] `B.md`" in checklist
    assert "- [ ] `C.md`" in checklist


def test_extract_shortcard_handles_identifier_table_fallbacks() -> None:
    markdown_text = """
## Säkerhetsdatablad
## NATRIUMKROMAT
Produktkod
SL088
## 1. Identifiering
## 3. Sammansättning/information om beståndsdelar
| Ingredienser | Namn | CAS | Andel |
| - | - | - | - |
|  | Natriumkromat | 7775-11-3 | 100% |
## 2. Faroidentifiering
H301 Giftigt vid förtäring.
P280
""".strip()

    shortcard, issues = _extract_shortcard(
        sds_ref="Na2CrO4",
        provider="external",
        md_file_name="Na2CrO4__external__undated.md",
        markdown_text=markdown_text,
        display_name="Natriumkromat (Na2CrO4)",
        ppe_default=[],
    )

    assert shortcard.product_no == "SL088"
    assert shortcard.cas == "7775-11-3"
    assert "missing_identity_identifiers" not in {issue.code for issue in issues}
