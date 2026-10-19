"""DigiExam workspace lineage fencing survives upgrade/downgrade and rejects duplicates."""

from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine

from tests.fixtures.database_fixtures import PooledDatabase
from tests.integration.migration_idempotency_support import assert_revision_is_idempotent

pytestmark = [pytest.mark.integration, pytest.mark.docker]


async def _assert_digiexam_lineage_fence(engine: AsyncEngine) -> None:
    async with engine.begin() as connection:
        definition = await connection.scalar(
            text(
                "SELECT indexdef FROM pg_indexes WHERE schemaname = 'public' "
                "AND indexname = 'uq_exam_answer_key_enrichment_jobs_digiexam_import_lineage'"
            )
        )
        assert definition is not None
        assert "UNIQUE INDEX" in definition
        assert "workspace_lineage_id" in definition
        assert "digiexam_import" in definition
        lineage = uuid4()
        owner = uuid4()
        insert = text(
            "INSERT INTO exam_answer_key_enrichment_jobs "
            "(id, owner_user_id, source_kind, status, input_filename, source_dxe, "
            "source_docx, workspace_lineage_id, workspace_document_revision) "
            "VALUES (:id, :owner, :kind, 'queued', :filename, :dxe, :docx, :lineage, 1)"
        )
        values = {
            "id": uuid4(),
            "owner": owner,
            "kind": "digiexam_import",
            "filename": "prov.dxe",
            "dxe": b"source",
            "docx": None,
            "lineage": lineage,
        }
        await connection.execute(insert, values)
        with pytest.raises(IntegrityError):
            async with connection.begin_nested():
                await connection.execute(insert, {**values, "id": uuid4()})
        # A new upload has its own lineage; the fence must not block the same teacher.
        await connection.execute(insert, {**values, "id": uuid4(), "lineage": uuid4()})
        # The predicate is DXE-only, not a second global lineage uniqueness rule.
        await connection.execute(
            insert,
            {
                **values,
                "id": uuid4(),
                "kind": "docx_import",
                "filename": "prov.docx",
                "dxe": None,
                "docx": b"source",
            },
        )
        count = await connection.scalar(
            text(
                "SELECT count(*) FROM exam_answer_key_enrichment_jobs WHERE owner_user_id = :owner"
            ),
            {"owner": owner},
        )
        assert count == 3


def test_migration_d71e4a6c9b20_is_idempotent_and_fences_only_digiexam_lineages(
    empty_module_database: PooledDatabase,
) -> None:
    assert_revision_is_idempotent(
        empty_module_database=empty_module_database,
        revision_id="d71e4a6c9b20",
        schema_assertion=_assert_digiexam_lineage_fence,
    )
