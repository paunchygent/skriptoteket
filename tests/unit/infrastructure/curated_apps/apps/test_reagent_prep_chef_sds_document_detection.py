"""Tests for SDS document validation and candidate URL filtering.

These tests pin root causes for previously observed failure modes where non-SDS PDFs were
selected as SDS candidates (e.g., OSHA SDS-format guidance, CFR regulations PDFs, NJ RTK
fact sheets). The pipeline must fail-closed (no SDS PDF) rather than cache misleading
documents and surface them as SDS in the UI.

Related:
  - `src/skriptoteket/infrastructure/curated_apps/apps/reagent_prep_chef/sds_parsers/text_extractors.py`
  - `src/skriptoteket/infrastructure/curated_apps/apps/reagent_prep_chef/sds_pdf_providers.py`
"""

from __future__ import annotations

from skriptoteket.infrastructure.curated_apps.apps.reagent_prep_chef.sds_parsers import (
    is_sds_document,
)
from skriptoteket.infrastructure.curated_apps.apps.reagent_prep_chef.sds_pdf_providers import (
    is_possible_pdf_url,
)


def test_is_possible_pdf_url_rejects_known_false_positive_documents() -> None:
    assert (
        is_possible_pdf_url("https://www.osha.gov/sites/default/files/publications/OSHA3514.pdf")
        is False
    )
    assert (
        is_possible_pdf_url(
            "https://www.govinfo.gov/content/pkg/CFR-2020-title49-vol2/pdf/"
            "CFR-2020-title49-vol2-part172.pdf"
        )
        is False
    )
    assert (
        is_possible_pdf_url(
            "https://www.govinfo.gov/content/pkg/CFR-2009-title49-vol2/pdf/"
            "CFR-2009-title49-vol2-part171.pdf"
        )
        is False
    )
    assert (
        is_possible_pdf_url("https://www.nj.gov/health/eoh/rtkweb/documents/fs/0209.pdf") is False
    )

    assert is_possible_pdf_url("https://example.test/sds.pdf") is True


def test_is_sds_document_accepts_real_sds_structure() -> None:
    text = "\n".join(
        [
            "Safety Data Sheet",
            "Section 1: Identification",
            "Section 2: Hazard(s) identification",
            "Section 3: Composition/information on ingredients",
            "Section 4: First aid measures",
            "Section 5: Fire-fighting measures",
            "Section 6: Accidental release measures",
            "Section 7: Handling and storage",
            "Section 8: Exposure controls/personal protection",
        ]
    )
    assert is_sds_document(text) is True


def test_is_sds_document_accepts_real_sds_that_mentions_right_to_know() -> None:
    text = "\n".join(
        [
            "Safety Data Sheet",
            "Section 1: Identification",
            "Section 2: Hazard(s) identification",
            "Section 3: Composition/information on ingredients",
            "Section 4: First aid measures",
            "Section 5: Fire-fighting measures",
            "Section 6: Accidental release measures",
            "Section 7: Handling and storage",
            "Section 8: Exposure controls/personal protection",
            "Section 15: Regulatory information",
            "US State Right to Know Regulations",
        ]
    )
    assert is_sds_document(text) is True


def test_is_sds_document_rejects_osha_sds_format_guidance() -> None:
    text = "\n".join(
        [
            "Hazard Communication Standard: Safety Data Sheets",
            "Section 1: Identification",
            "This section identifies the chemical on the SDS as well as the recommended uses.",
            "Section 2: Hazard(s) identification",
            "Section 3: Composition/information on ingredients",
            "Section 4: First aid measures",
            "Section 5: Fire-fighting measures",
            "Section 6: Accidental release measures",
            "Section 7: Handling and storage",
            "Section 8: Exposure controls/personal protection",
        ]
    )
    assert is_sds_document(text) is False


def test_is_sds_document_rejects_cfr_hazmat_regulations_pdf() -> None:
    text = "\n".join(
        [
            "Safety Data Sheet",
            "PART 172—HAZARDOUS MATERIALS",
            "sub-section 33.2.1",
            "6. No label is required for a material classed as a combustible liquid.",
        ]
    )
    assert is_sds_document(text) is False


def test_is_sds_document_rejects_nj_right_to_know_fact_sheet() -> None:
    text = "\n".join(
        [
            "Safety Data Sheet",
            "Right to Know",
            "Hazardous Substance Fact Sheet",
            "Common Name: BENZOIC ACID",
        ]
    )
    assert is_sds_document(text) is False
