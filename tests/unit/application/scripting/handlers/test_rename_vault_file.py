from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest

from skriptoteket.application.curated_apps.exam_answer_key_enrichment import (
    ExamAnswerKeyEnrichmentJob,
    ExamAnswerKeyEnrichmentJobStatus,
    ExamAnswerKeySourceKind,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_conversion_progress import (
    _version_name,
)
from skriptoteket.application.scripting.handlers.rename_vault_file import RenameVaultFileHandler
from skriptoteket.application.scripting.vault import RenameVaultFileCommand
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.scripting.vault import VaultFile, VaultFileSourceKind
from skriptoteket.protocols.exam_index import ExamIndexRepositoryProtocol
from tests.fixtures.identity_fixtures import make_user
from tests.unit.application.scripting.handlers.vault_test_support import FakeUow, FakeVaultFileRepo

_NOW = datetime(2026, 10, 16, tzinfo=UTC)


def _handler(repo: FakeVaultFileRepo) -> RenameVaultFileHandler:
    index = AsyncMock(spec=ExamIndexRepositoryProtocol)
    index.get.return_value = None
    return RenameVaultFileHandler(uow=FakeUow(), vault_files=repo, index=index)


def test_conversion_version_name_keeps_teacher_rename_after_the_first_version() -> None:
    job = ExamAnswerKeyEnrichmentJob(
        id=uuid4(),
        owner_user_id=uuid4(),
        source_kind=ExamAnswerKeySourceKind.DOCX_IMPORT,
        status=ExamAnswerKeyEnrichmentJobStatus.RUNNING,
        input_filename="Ursprung.docx",
        source_docx=b"docx",
        workspace_lineage_id=uuid4(),
        workspace_document_revision=1,
        available_at=_NOW,
        created_at=_NOW,
        updated_at=_NOW,
    )
    renamed_head = _file(job.owner_user_id, name="Lärarens namn.provdokument.zip")
    assert _version_name(job) == "Ursprung.provdokument.zip"
    assert _version_name(job, renamed_head) == "Lärarens namn.provdokument.zip"


def _file(user_id: UUID, **updates: object) -> VaultFile:
    file = VaultFile(
        id=uuid4(),
        user_id=user_id,
        name="Gamla.pdf",
        bytes=412,
        source_kind=VaultFileSourceKind.APP_EXPORT,
        source_run_id=uuid4(),
        source_artifact_id="artifacts/report.pdf",
        created_at=_NOW,
    )
    return file.model_copy(update=updates)


@pytest.mark.asyncio
@pytest.mark.parametrize("case", ["missing", "foreign", "trashed"])
async def test_inaccessible_records_are_not_found_and_never_changed(case: str) -> None:
    actor = make_user()
    repo = FakeVaultFileRepo()
    file = _file(
        uuid4() if case == "foreign" else actor.id, deleted_at=_NOW if case == "trashed" else None
    )
    if case != "missing":
        await repo.create(file=file)
    with pytest.raises(DomainError) as caught:
        await _handler(repo).handle(
            actor=actor,
            command=RenameVaultFileCommand(file_id=file.id, stem="Nytt"),
        )
    assert caught.value.code is ErrorCode.NOT_FOUND
    assert await repo.get_by_id(file_id=file.id) == (None if case == "missing" else file)


@pytest.mark.asyncio
@pytest.mark.parametrize("other_state", ["active", "trashed", "foreign"])
async def test_collision_is_owner_scoped_and_only_counts_active_records(other_state: str) -> None:
    actor = make_user()
    repo = FakeVaultFileRepo()
    file = _file(actor.id)
    other = _file(
        uuid4() if other_state == "foreign" else actor.id,
        name="Nytt.pdf",
        deleted_at=_NOW if other_state == "trashed" else None,
    )
    await repo.create(file=file)
    await repo.create(file=other)
    handler = _handler(repo)
    command = RenameVaultFileCommand(file_id=file.id, stem="Nytt")
    if other_state == "active":
        with pytest.raises(DomainError) as caught:
            await handler.handle(actor=actor, command=command)
        assert caught.value.code is ErrorCode.VALIDATION_ERROR
        assert caught.value.message == "Namnet används redan av en annan fil."
        assert caught.value.details["code"] == "vault_name_in_use"
        assert await repo.get_by_id(file_id=file.id) == file
    else:
        result = await handler.handle(actor=actor, command=command)
        assert result.file.name == "Nytt.pdf"
    assert await repo.get_by_id(file_id=other.id) == other


@pytest.mark.asyncio
async def test_lineage_rename_renames_the_exam_file_including_trash_and_spares_its_export() -> None:
    actor = make_user()
    repo = FakeVaultFileRepo()
    lineage = uuid4()
    exam = _file(
        actor.id,
        name="Gamla.provdokument.zip",
        document_lineage_id=lineage,
        document_version=3,
        source_artifact_id=f"documents.conversion_hub:exam-workspace:{lineage}",
    )
    trashed = _file(
        actor.id,
        name="Gamla.provdokument.zip",
        document_lineage_id=lineage,
        document_version=1,
        source_artifact_id=f"documents.conversion_hub:exam-workspace:{lineage}",
        deleted_at=_NOW,
    )
    export = _file(
        actor.id,
        name="Gamla-qti.zip",
        document_lineage_id=lineage,
        document_version=3,
        export_format="qti",
        source_artifact_id=f"documents.conversion_hub:exam-workspace:{lineage}:qti",
    )
    unrelated = _file(actor.id, document_lineage_id=uuid4())
    for file in (exam, trashed, export, unrelated):
        await repo.create(file=file)
    result = await _handler(repo).handle(
        actor=actor,
        command=RenameVaultFileCommand(file_id=exam.id, stem="Nytt"),
    )
    assert result.file.id == exam.id
    assert result.file.name == "Nytt.provdokument.zip"
    assert set(result.renamed_file_ids) == {exam.id, trashed.id}
    for before in (exam, trashed):
        after = await repo.get_by_id(file_id=before.id)
        assert after is not None
        assert after.name == "Nytt.provdokument.zip"
        assert after.model_dump(exclude={"name"}) == before.model_dump(exclude={"name"})
    assert await repo.get_by_id(file_id=export.id) == export
    assert await repo.get_by_id(file_id=unrelated.id) == unrelated


@pytest.mark.asyncio
async def test_non_exam_lineage_without_source_reference_keeps_last_suffix() -> None:
    actor = make_user()
    repo = FakeVaultFileRepo()
    file = _file(actor.id, document_lineage_id=uuid4(), source_artifact_id=None)
    await repo.create(file=file)
    result = await _handler(repo).handle(
        actor=actor,
        command=RenameVaultFileCommand(file_id=file.id, stem="Nytt"),
    )
    assert result.file.name == "Nytt.pdf"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("name", "source", "expected"),
    [
        ("Exam.zip", "documents.conversion_hub:exam-workspace:1", "Nytt.provdokument.zip"),
        ("Exam.provdokument.zip", "ordinary-export", "Nytt.zip"),
        ("Bilaga.pdf", None, "Nytt.pdf"),
        ("Anteckningar", None, "Nytt"),
    ],
)
async def test_standalone_rename_classifies_the_record_and_changes_only_it(
    name: str,
    source: str | None,
    expected: str,
) -> None:
    actor = make_user()
    repo = FakeVaultFileRepo()
    file = _file(
        actor.id,
        name=name,
        source_artifact_id=source,
        document_lineage_id=uuid4() if source and source.startswith("documents.") else None,
        document_version=1,
    )
    unrelated = _file(actor.id)
    await repo.create(file=file)
    await repo.create(file=unrelated)
    result = await _handler(repo).handle(
        actor=actor,
        command=RenameVaultFileCommand(file_id=file.id, stem="Nytt"),
    )
    assert result.file.name == expected
    assert result.exam_summary is None
    assert result.renamed_file_ids == (file.id,)
    updated = await repo.get_by_id(file_id=file.id)
    assert updated is not None
    assert updated.model_dump(exclude={"name"}) == file.model_dump(exclude={"name"})
    assert await repo.get_by_id(file_id=unrelated.id) == unrelated
