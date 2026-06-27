"""Sir Convert status vocabulary contract tests.

Domain purpose:
    Prove Skriptoteket translates the typed Sir Convert v2 job lifecycle into
    local product-facing lifecycles exhaustively.

Relationships:
    - Guards `ConversionHubJobStatus.from_sir_convert_status`.
    - Guards `PublicExamConverterJobStatus.from_sir_convert_status`.
    - Complements Sir Convert client-boundary parsing tests.
"""

from __future__ import annotations

import pytest

from skriptoteket.application.curated_apps.conversion_hub import ConversionHubJobStatus
from skriptoteket.application.curated_apps.public_exam_converter import (
    PublicExamConverterJobStatus,
)
from skriptoteket.protocols.sir_convert_a_lot_v2 import SirConvertJobStatusV2


@pytest.mark.unit
def test_conversion_hub_status_mapping_covers_every_sir_convert_status() -> None:
    expected = {
        SirConvertJobStatusV2.QUEUED: ConversionHubJobStatus.QUEUED,
        SirConvertJobStatusV2.RUNNING: ConversionHubJobStatus.PROCESSING,
        SirConvertJobStatusV2.SUCCEEDED: ConversionHubJobStatus.SUCCEEDED,
        SirConvertJobStatusV2.FAILED: ConversionHubJobStatus.FAILED,
        SirConvertJobStatusV2.CANCELED: ConversionHubJobStatus.CANCELED,
    }

    assert {
        status: ConversionHubJobStatus.from_sir_convert_status(status)
        for status in SirConvertJobStatusV2
    } == expected


@pytest.mark.unit
def test_public_exam_converter_status_mapping_covers_every_sir_convert_status() -> None:
    expected = {
        SirConvertJobStatusV2.QUEUED: PublicExamConverterJobStatus.QUEUED,
        SirConvertJobStatusV2.RUNNING: PublicExamConverterJobStatus.PROCESSING,
        SirConvertJobStatusV2.SUCCEEDED: PublicExamConverterJobStatus.SUCCEEDED,
        SirConvertJobStatusV2.FAILED: PublicExamConverterJobStatus.FAILED,
        SirConvertJobStatusV2.CANCELED: PublicExamConverterJobStatus.CANCELED,
    }

    assert {
        status: PublicExamConverterJobStatus.from_sir_convert_status(status)
        for status in SirConvertJobStatusV2
    } == expected
