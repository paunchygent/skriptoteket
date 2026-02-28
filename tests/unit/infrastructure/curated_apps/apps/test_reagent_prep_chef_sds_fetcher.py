from __future__ import annotations

from typing import Iterable

import httpx
import pytest
import structlog

from skriptoteket.domain.curated_apps.reagent_prep_chef.models import HazardEntry
from skriptoteket.infrastructure.curated_apps.apps.reagent_prep_chef.sds_fetcher import (
    PubChemSdsFetcher,
)
from skriptoteket.infrastructure.curated_apps.apps.reagent_prep_chef.sds_fetcher_settings import (
    SdsFetcherSettings,
)
from skriptoteket.infrastructure.curated_apps.apps.reagent_prep_chef.sds_pdf_providers import (
    SdsPdfCandidate,
    SdsPdfProviderContext,
    SdsPdfProviderRegistry,
)
from skriptoteket.infrastructure.curated_apps.apps.reagent_prep_chef.sds_query_variants import (
    normalize_formula_variants,
)


def _build_pdf_with_text(text: str) -> bytes:
    escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    content = f"BT /F1 12 Tf 72 720 Td ({escaped}) Tj ET"
    objects = [
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n",
        b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n",
        (
            b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj\n"
        ),
        (
            f"4 0 obj << /Length {len(content)} >> stream\n{content}\nendstream endobj\n".encode(
                "utf-8"
            )
        ),
        b"5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n",
    ]

    header = b"%PDF-1.4\n"
    offsets = []
    cursor = len(header)
    for obj in objects:
        offsets.append(cursor)
        cursor += len(obj)

    xref_offset = cursor
    xref_lines = ["xref\n0 6\n0000000000 65535 f \n"]
    for offset in offsets:
        xref_lines.append(f"{offset:010d} 00000 n \n")

    trailer = f"trailer << /Size 6 /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n"
    return b"".join(
        [header, *objects, "".join(xref_lines).encode("utf-8"), trailer.encode("utf-8")]
    )


class FakeSdsClient:
    def __init__(self, *, url: str, pdf_bytes: bytes) -> None:
        self._url = url
        self._pdf_bytes = pdf_bytes

    async def get(self, url: str, *, params: dict | None = None) -> httpx.Response:
        if url != self._url:
            raise AssertionError(f"Unexpected URL: {url}")
        request = httpx.Request("GET", url)
        return httpx.Response(
            200,
            request=request,
            content=self._pdf_bytes,
            headers={"content-type": "application/pdf"},
        )

    async def aclose(self) -> None:
        return None


def test_normalize_formula_variants_expands_parentheses() -> None:
    variants = normalize_formula_variants("(NH4)2CO3")
    assert "CH8N2O3" in variants


def test_normalize_formula_variants_expands_hydrate_multiplier() -> None:
    variants = normalize_formula_variants("H2C2O4·2H2O")
    assert "C2H6O6" in variants


@pytest.mark.asyncio
async def test_fetcher_tries_multiple_cids_until_ghs_found() -> None:
    pdf_bytes = _build_pdf_with_text(
        "Safety Data Sheet\n"
        "Section 1 Identification\n"
        "Section 2 Hazards identification\n"
        "H302: C >= 10% w/w\n"
        "Section 3 Composition/information on ingredients\n"
        "Section 4 First aid measures\n"
        "Section 5 Fire-fighting measures\n"
        "Section 6 Accidental release measures\n"
        "Section 7 Handling and storage\n"
        "Section 8 Exposure controls/personal protection\n"
        "Section 10 Stability and Reactivity\n"
        "Incompatible materials: Acids"
    )
    pdf_url = "https://example.test/sds.pdf"

    class FakePubChem:
        base_url = "https://pubchem.test"

        async def resolve_cids(
            self, *, queries: Iterable[str], max_candidates: int | None = None
        ) -> list[int]:
            return [111, 222]

        async def fetch_lcss(self, *, cid: int) -> dict:
            if cid == 111:
                return {"Record": {"Section": []}}
            return {
                "Record": {
                    "Section": [
                        {
                            "TOCHeading": "GHS Classification",
                            "Information": [
                                {
                                    "Name": "GHS Hazard Statements",
                                    "Value": {
                                        "StringWithMarkup": [
                                            {"String": "H302 Harmful if swallowed."}
                                        ]
                                    },
                                },
                                {
                                    "Name": "Signal",
                                    "Value": {"StringWithMarkup": [{"String": "Warning"}]},
                                },
                                {
                                    "Name": "Pictogram(s)",
                                    "Value": {
                                        "StringWithMarkup": [
                                            {"Markup": [{"URL": "https://example.test/GHS07.svg"}]}
                                        ]
                                    },
                                },
                            ],
                        }
                    ]
                }
            }

        async def fetch_heading(self, *, cid: int, heading: str) -> dict:
            if heading == "Density":
                return {
                    "Record": {
                        "Section": [
                            {
                                "TOCHeading": "Density",
                                "Information": [
                                    {"Value": {"StringWithMarkup": [{"String": "1.0 g/mL"}]}}
                                ],
                            }
                        ]
                    }
                }
            request = httpx.Request("GET", "https://pubchem.test")
            response = httpx.Response(404, request=request)
            raise httpx.HTTPStatusError(
                "Not found",
                request=request,
                response=response,
            )

        async def fetch_linkout(self, *, cid: int) -> dict:
            return {
                "Linkout": {
                    "ObjUrl": [
                        {
                            "Url": pdf_url,
                            "LinkName": "Safety Data Sheet",
                        }
                    ]
                }
            }

        async def fetch_properties_batch(
            self, *, cids: Iterable[int], properties: list[str]
        ) -> dict:
            return {}

        async def autocomplete_compound(
            self, *, query: str, max_terms: int | None = None
        ) -> list[str]:
            return []

    fetcher = PubChemSdsFetcher(
        pubchem=FakePubChem(),
        settings=SdsFetcherSettings(
            timeout_seconds=1,
            user_agent="test",
            cid_candidate_limit=5,
        ),
        sds_http=FakeSdsClient(url=pdf_url, pdf_bytes=pdf_bytes),
    )
    hazard = HazardEntry(key="NH4Cl", display_name="Test")
    result = await fetcher.fetch(hazard=hazard)
    assert "H302" in result.hazard_codes
    assert result.media_type == "application/pdf"


@pytest.mark.asyncio
async def test_fetcher_expands_candidates_when_limit_reached() -> None:
    pdf_bytes = _build_pdf_with_text(
        "Safety Data Sheet\n"
        "Section 1 Identification\n"
        "Section 2 Hazards identification\n"
        "H302: C >= 10% w/w\n"
        "Section 3 Composition/information on ingredients\n"
        "Section 4 First aid measures\n"
        "Section 5 Fire-fighting measures\n"
        "Section 6 Accidental release measures\n"
        "Section 7 Handling and storage\n"
        "Section 8 Exposure controls/personal protection\n"
        "Section 10 Stability and Reactivity\n"
        "Incompatible materials: Acids"
    )
    pdf_url = "https://example.test/sds.pdf"

    class FakePubChem:
        base_url = "https://pubchem.test"

        async def resolve_cids(
            self, *, queries: Iterable[str], max_candidates: int | None = None
        ) -> list[int]:
            if max_candidates == 2:
                return [111, 222]
            if max_candidates is None:
                return [111, 222, 333]
            return []

        async def fetch_lcss(self, *, cid: int) -> dict:
            if cid == 333:
                return {
                    "Record": {
                        "Section": [
                            {
                                "TOCHeading": "GHS Classification",
                                "Information": [
                                    {
                                        "Name": "GHS Hazard Statements",
                                        "Value": {
                                            "StringWithMarkup": [
                                                {"String": "H302 Harmful if swallowed."}
                                            ]
                                        },
                                    }
                                ],
                            }
                        ]
                    }
                }
            return {"Record": {"Section": []}}

        async def fetch_heading(self, *, cid: int, heading: str) -> dict:
            if heading == "Density":
                return {
                    "Record": {
                        "Section": [
                            {
                                "TOCHeading": "Density",
                                "Information": [
                                    {"Value": {"StringWithMarkup": [{"String": "1.0 g/mL"}]}}
                                ],
                            }
                        ]
                    }
                }
            request = httpx.Request("GET", "https://pubchem.test")
            response = httpx.Response(404, request=request)
            raise httpx.HTTPStatusError(
                "Not found",
                request=request,
                response=response,
            )

        async def fetch_linkout(self, *, cid: int) -> dict:
            return {
                "Linkout": {
                    "ObjUrl": [
                        {
                            "Url": pdf_url,
                            "LinkName": "Safety Data Sheet",
                        }
                    ]
                }
            }

        async def fetch_properties_batch(
            self, *, cids: Iterable[int], properties: list[str]
        ) -> dict:
            return {}

        async def autocomplete_compound(
            self, *, query: str, max_terms: int | None = None
        ) -> list[str]:
            return []

    fetcher = PubChemSdsFetcher(
        pubchem=FakePubChem(),
        settings=SdsFetcherSettings(
            timeout_seconds=1,
            user_agent="test",
            cid_candidate_limit=2,
        ),
        sds_http=FakeSdsClient(url=pdf_url, pdf_bytes=pdf_bytes),
    )
    hazard = HazardEntry(key="H2C2O4·2H2O", display_name="Oxalsyra (dihydrat)")
    result = await fetcher.fetch(hazard=hazard)
    assert "H302" in result.hazard_codes


@pytest.mark.asyncio
async def test_sds_provider_registry_dedupes_candidates_in_order() -> None:
    class ProviderA:
        name = "a"

        async def collect_candidates(
            self, *, context: SdsPdfProviderContext, log: structlog.stdlib.BoundLogger
        ) -> list[SdsPdfCandidate]:
            return [
                SdsPdfCandidate(url="https://example.test/a.pdf", label="A", source=self.name),
                SdsPdfCandidate(
                    url="https://example.test/shared.pdf", label=None, source=self.name
                ),
            ]

    class ProviderB:
        name = "b"

        async def collect_candidates(
            self, *, context: SdsPdfProviderContext, log: structlog.stdlib.BoundLogger
        ) -> list[SdsPdfCandidate]:
            return [
                SdsPdfCandidate(
                    url="https://example.test/shared.pdf", label=None, source=self.name
                ),
                SdsPdfCandidate(url="https://example.test/b.pdf", label="B", source=self.name),
            ]

    registry = SdsPdfProviderRegistry(providers=[ProviderA(), ProviderB()])
    context = SdsPdfProviderContext(
        hazard=HazardEntry(key="NaCl", display_name="Salt"),
        cid=1,
        lcss_payload={},
        linkout_payload=None,
        safety_payload=None,
    )
    candidates = await registry.collect_candidates(context=context, log=structlog.get_logger())
    assert [candidate.url for candidate in candidates] == [
        "https://example.test/a.pdf",
        "https://example.test/shared.pdf",
        "https://example.test/b.pdf",
    ]
