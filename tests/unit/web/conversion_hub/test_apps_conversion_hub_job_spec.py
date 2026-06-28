"""Unit tests for Conversion Hub job spec mapping to Sir Convert-a-Lot v2."""

from __future__ import annotations

import pytest

from skriptoteket.application.curated_apps.conversion_hub import (
    ConversionHubJobSpecV2,
    ConversionHubOutputFormatV2,
    ConversionHubPdfLayoutV2,
    ConversionHubPdfOrientationV2,
    ConversionHubPdfPaperSizeV2,
    ConversionHubSourceFormatV2,
    build_conversion_hub_v2_job_spec,
)
from skriptoteket.domain.errors import DomainError, ErrorCode


@pytest.mark.unit
def test_build_v2_job_spec_includes_pdf_layout_only_for_pdf_outputs() -> None:
    spec = ConversionHubJobSpecV2(
        source_format=ConversionHubSourceFormatV2.HTML,
        output_format=ConversionHubOutputFormatV2.PDF,
        pdf_layout=ConversionHubPdfLayoutV2(
            paper_size=ConversionHubPdfPaperSizeV2.A5,
            orientation=ConversionHubPdfOrientationV2.LANDSCAPE,
            margins_mm=10,
        ),
    )
    payload = build_conversion_hub_v2_job_spec(spec=spec, filename="in.html")
    assert payload["api_version"] == "v2"
    assert isinstance(payload["conversion"], dict)
    conversion = payload["conversion"]
    assert conversion.get("output_format") == "pdf"
    pdf_layout = conversion.get("pdf_layout")
    assert isinstance(pdf_layout, dict)
    assert pdf_layout.get("paper_size") == "a5"
    assert pdf_layout.get("orientation") == "landscape"
    assert pdf_layout.get("margins_mm") == 10


@pytest.mark.unit
def test_build_v2_job_spec_rejects_pdf_layout_for_non_pdf_outputs() -> None:
    spec = ConversionHubJobSpecV2(
        source_format=ConversionHubSourceFormatV2.HTML,
        output_format=ConversionHubOutputFormatV2.MD,
        pdf_layout=ConversionHubPdfLayoutV2(),
    )
    with pytest.raises(DomainError) as excinfo:
        build_conversion_hub_v2_job_spec(spec=spec, filename="in.html")
    assert excinfo.value.code == ErrorCode.VALIDATION_ERROR


@pytest.mark.unit
def test_build_v2_job_spec_adds_required_defaults_for_pdf_sources() -> None:
    spec = ConversionHubJobSpecV2(
        source_format=ConversionHubSourceFormatV2.PDF,
        output_format=ConversionHubOutputFormatV2.MD,
        pdf_layout=None,
    )
    payload = build_conversion_hub_v2_job_spec(spec=spec, filename="in.pdf")
    assert isinstance(payload.get("pdf_options"), dict)
    assert isinstance(payload.get("execution"), dict)
