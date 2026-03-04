"""Unit tests for the Carl Roth SDS downloader pipeline script."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.download_reagent_prep_chef_sds_pdfs import (
    RothHtmlParser,
    RothSelector,
    SdsDocument,
    _atlas_fallback_queries,
    _build_search_queries,
    _dedupe_nonempty_strings,
    _extract_locale_codes,
    _load_target_overrides,
    _resolve_revision,
)


def test_extract_locale_codes_parses_country_and_language() -> None:
    country, language = _extract_locale_codes("https://www.carlroth.com/medias/SDB-5741-SE-SV.pdf")
    assert country == "SE"
    assert language == "SV"


def test_extract_locale_codes_returns_none_for_non_matching_pattern() -> None:
    country, language = _extract_locale_codes("https://www.carlroth.com/medias/SPEZ-5741-EN.pdf")
    assert country is None
    assert language is None


def test_extract_product_candidates_deduplicates_and_filters_noise() -> None:
    html = """
    <html><body>
      <a href="/com/en/general-reagents/sodium-chloride/p/p029.5">Sodium chloride, 25 kg</a>
      <a href="/com/en/general-reagents/sodium-chloride/p/p029.5">Go to product selection</a>
      <a href="/com/en/general-reagents/sodium-chloride/p/p029.5">NEW</a>
      <a href="/com/en/Wissenswertes">Downloads</a>
    </body></html>
    """

    candidates = RothHtmlParser.extract_product_candidates(html=html)

    assert len(candidates) == 1
    assert candidates[0].title == "Sodium chloride, 25 kg"
    assert candidates[0].url.endswith("/com/en/general-reagents/sodium-chloride/p/p029.5")


def test_extract_sds_documents_collects_sdb_pdf_links() -> None:
    html = """
    <html><body>
      <a href="/medias/SDB-5741-SE-SV.pdf?context=abc">Security datasheet Sweden / Swedish</a>
      <a href="/medias/SDB-5741-DE-EN.pdf?context=def">Security datasheet Germany / English</a>
      <a href="/medias/SPEZ-5741-EN.pdf?context=ghi">Specification / English</a>
    </body></html>
    """

    docs = RothHtmlParser.extract_sds_documents(html=html)

    assert len(docs) == 2
    assert any(doc.country_code == "SE" and doc.language_code == "SV" for doc in docs)
    assert any(doc.country_code == "DE" and doc.language_code == "EN" for doc in docs)


def test_selector_prefers_swedish_then_english() -> None:
    selector = RothSelector()
    docs = [
        SdsDocument(
            label="Security datasheet Germany / English",
            url="https://www.carlroth.com/medias/SDB-1-DE-EN.pdf?context=x",
            country_code="DE",
            language_code="EN",
        ),
        SdsDocument(
            label="Security datasheet Sweden / Swedish",
            url="https://www.carlroth.com/medias/SDB-1-SE-SV.pdf?context=y",
            country_code="SE",
            language_code="SV",
        ),
    ]

    selected = selector.choose_sds_document(docs=docs)

    assert selected is not None
    assert selected.language_code == "SV"
    assert selected.country_code == "SE"


def test_build_search_queries_deduplicates() -> None:
    hazard = {
        "key": "NaCl",
        "display_name": "Natriumklorid (NaCl)",
        "search_aliases": ["Sodium chloride", "Sodium chloride", "Common salt"],
    }

    queries = _build_search_queries(hazard=hazard)

    assert queries[0] == "Sodium chloride"
    assert "Common salt" in queries
    assert "Natriumklorid" in queries
    assert "NaCl" in queries


def test_dedupe_nonempty_strings_handles_spacing_and_case() -> None:
    values = ["  Hydrogen peroxide ", "hydrogen peroxide", "", " H2O2 "]
    deduped = _dedupe_nonempty_strings(values)
    assert deduped == ["Hydrogen peroxide", "H2O2"]


def test_load_target_overrides_reads_product_urls_and_queries(tmp_path: Path) -> None:
    payload = {
        "version": 1,
        "targets": {
            "H2O2": {
                "prepend_queries": ["Hydrogen peroxide", "hydrogen peroxide"],
                "product_urls": [
                    "https://www.carlroth.com/com/en/a-to-z/hydrogen-peroxide/p/cp26.1",
                ],
            }
        },
    }
    path = tmp_path / "overrides.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    overrides = _load_target_overrides(path=path)

    assert "H2O2" in overrides
    override = overrides["H2O2"]
    assert override.prepend_queries == ("Hydrogen peroxide",)
    assert override.product_urls == (
        "https://www.carlroth.com/com/en/a-to-z/hydrogen-peroxide/p/cp26.1",
    )


def test_resolve_revision_ignores_epoch_like_header() -> None:
    revision = _resolve_revision(headers={"last-modified": "Thu, 01 Jan 1970 00:00:01 GMT"})
    assert revision == "undated"


def test_resolve_revision_uses_valid_last_modified_date() -> None:
    revision = _resolve_revision(headers={"last-modified": "Wed, 17 Jul 2024 13:21:00 GMT"})
    assert revision == "2024-07-17"


def test_atlas_fallback_queries_include_swedish_and_english() -> None:
    target_like = type(
        "TargetLike",
        (),
        {
            "display_name": "Natriumklorid",
            "search_queries": ("Sodium chloride",),
            "key": "NaCl",
        },
    )()

    fallback = _atlas_fallback_queries(target=target_like)

    assert "säkerhetsdatablad" in fallback[0]
    assert "SDS" in fallback[1]
    assert fallback[2].startswith("NaCl")
