"""Document Converter saved-file request contract tests.

Purpose:
    Prove the protected Document Converter saved-file API accepts only the
    ordered `source_refs` batch payload.

Relationships:
    Complements the route facade tests in `test_apps_document_converter_api`.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from skriptoteket.application.curated_apps.conversion_hub import (
    ConversionHubJobSpecV2,
    ConversionHubOutputFormatV2,
    ConversionHubSourceFormatV2,
)
from skriptoteket.application.curated_apps.document_converter import (
    SubmitDocumentConverterSavedFileRequest,
)
from skriptoteket.domain.scripting.file_refs import build_vault_file_ref


@pytest.mark.unit
def test_submit_saved_file_request_requires_canonical_source_refs() -> None:
    spec = ConversionHubJobSpecV2(
        source_format=ConversionHubSourceFormatV2.HTML,
        output_format=ConversionHubOutputFormatV2.PDF,
    ).model_dump(mode="json")

    with pytest.raises(ValueError):
        SubmitDocumentConverterSavedFileRequest.model_validate(
            {"job_spec": spec, "source_ref": build_vault_file_ref(file_id=uuid4())}
        )
    with pytest.raises(ValueError):
        SubmitDocumentConverterSavedFileRequest.model_validate(
            {"job_spec": spec, "source_refs": []}
        )

    request = SubmitDocumentConverterSavedFileRequest.model_validate(
        {
            "job_spec": spec,
            "source_refs": [
                build_vault_file_ref(file_id=uuid4()),
                build_vault_file_ref(file_id=uuid4()),
            ],
        }
    )
    assert len(request.source_refs) == 2
