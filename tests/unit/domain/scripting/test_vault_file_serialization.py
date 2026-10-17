"""The internal trash flag stays inside the domain and the database.

`trashed_with_exam` tells the restore which saved exports came along when the exam went
to the trash. It is lifecycle bookkeeping, not a user-visible property, so it must never
appear in a serialized file payload or in the serialization schema the API shape is
generated from.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from skriptoteket.domain.scripting.vault import VaultFile, VaultFileSourceKind


@pytest.mark.unit
def test_trashed_with_exam_never_reaches_a_payload_or_a_serialization_schema() -> None:
    file = VaultFile(
        id=uuid4(),
        user_id=uuid4(),
        name="Prov.provdokument.zip",
        bytes=100,
        source_kind=VaultFileSourceKind.APP_EXPORT,
        document_lineage_id=uuid4(),
        document_version=1,
        created_at=datetime(2026, 10, 17, 12, 0, tzinfo=UTC),
        deleted_at=datetime(2026, 10, 17, 12, 0, tzinfo=UTC),
        trashed_with_exam=True,
    )

    assert file.trashed_with_exam is True
    assert "trashed_with_exam" not in file.model_dump()
    assert "trashed_with_exam" not in file.model_dump(mode="json")

    properties = VaultFile.model_json_schema(mode="serialization").get("properties", {})
    assert "trashed_with_exam" not in properties
