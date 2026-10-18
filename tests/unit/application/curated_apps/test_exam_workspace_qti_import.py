"""QTI package import parses to a native container and saves revision one.

The parse handler runs against the REAL package reader, the REAL export and the
REAL container codec; it takes no store at all, so parsing cannot touch one.
Only the vault and index are fakes.
"""

import hashlib
from uuid import uuid4

import pytest

from skriptoteket.application.curated_apps.exam_workspace_exports import (
    build_native_examnet_qti_package,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_document_store import (
    ExamWorkspaceDocumentStore,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_qti_import import (
    ImportExamWorkspaceQtiDocumentHandler,
    ParseExamWorkspaceQtiPackageHandler,
)
from skriptoteket.config import Settings
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
    NativeExamDocumentOrigin,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeExamItemKind,
)
from skriptoteket.domain.curated_apps.exam_workspace.shared_body import body_plain_text
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.scripting.vault import VaultUsage
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_container import (
    ExamWorkspaceContainerCodec,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.examnet_qti_package_reader import (  # noqa: E501
    ExamNetQtiPackageReader,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.examnet_qti_writer import (
    ExamNetQtiPackageWriter,
)
from tests.fixtures.application_fixtures import FakeUow
from tests.fixtures.time_fixtures import FixedClock
from tests.unit.application.curated_apps.handlers.exam_index_test_support import (
    InMemoryExamIndexRepository,
)
from tests.unit.application.curated_apps.handlers.test_conversion_hub_jobs import (
    SequenceIdGenerator,
)
from tests.unit.application.curated_apps.handlers.test_document_converter_artifact_saves import (
    InMemoryVaultStorage,
    InMemoryVaultUsageRepository,
)
from tests.unit.application.curated_apps.handlers.test_exam_workspace_documents import (
    _NOW,
    _actor,
    _settings,
)
from tests.unit.application.curated_apps.handlers.vault_file_repository_test_support import (
    InMemoryVaultFileRepository,
)
from tests.unit.domain.curated_apps.exam_workspace.native_exam_test_builders import (
    make_gap_fill_item,
    make_single_choice_item,
)

_COURSE_KEY = "SVESVE02"


def _package_bytes() -> bytes:
    """Real exported QTI package bytes: one choice question and one gap-fill question."""
    document = NativeExamDocument(
        document_id=uuid4(),
        revision=1,
        title="QTI-avsetning",
        items=(
            make_single_choice_item(),
            make_gap_fill_item(sequence=2, item_id="item_002"),
        ),
        origin=NativeExamDocumentOrigin(kind="created"),
    )
    package, _report = build_native_examnet_qti_package(
        document, package_name="qti-avsetning", qti_writer=ExamNetQtiPackageWriter()
    )
    return package


def _parse_handler(settings: Settings) -> ParseExamWorkspaceQtiPackageHandler:
    return ParseExamWorkspaceQtiPackageHandler(
        reader=ExamNetQtiPackageReader(),
        settings=settings,
        id_generator=SequenceIdGenerator([uuid4() for _ in range(5)]),
    )


def _store(settings: Settings) -> tuple[ExamWorkspaceDocumentStore, InMemoryVaultFileRepository]:
    vault_files = InMemoryVaultFileRepository()
    store = ExamWorkspaceDocumentStore(
        vault_files=vault_files,
        vault_usage=InMemoryVaultUsageRepository(
            usage=VaultUsage(user_id=_actor().id, bytes_total=0, updated_at=_NOW)
        ),
        vault_storage=InMemoryVaultStorage(),
        uow=FakeUow(),
        clock=FixedClock(_NOW),
        settings=settings,
        index=InMemoryExamIndexRepository(vault_files),
        codec=ExamWorkspaceContainerCodec(),
    )
    return store, vault_files


@pytest.mark.asyncio
async def test_parse_maps_real_package_to_native_qti_import_container():
    content = _package_bytes()
    handler = _parse_handler(_settings())

    container = handler.handle(filename="prov.zip", content=content, course_key=_COURSE_KEY)

    assert container.document.origin.kind == "qti_import"
    assert container.document.origin.source_filename == "prov.zip"
    assert container.document.origin.source_sha256 == hashlib.sha256(content).hexdigest()
    assert container.document.revision == 1
    assert container.document.header.course is not None
    assert container.document.header.course.key == _COURSE_KEY
    assert container.document.header.course.name == "Svenska 2"
    assert [item.kind for item in container.document.items] == [
        NativeExamItemKind.SINGLE_CHOICE,
        NativeExamItemKind.GAP_FILL,
    ]
    assert body_plain_text(container.document.items[0].body) == "Vilket är huvudordet?"
    assert container.notes == ()


@pytest.mark.asyncio
async def test_parse_accepts_a_case_insensitive_zip_suffix():
    handler = _parse_handler(_settings())

    container = handler.handle(filename="Paket.ZIP", content=_package_bytes(), course_key=None)

    assert container.document.origin.source_filename == "Paket.ZIP"


@pytest.mark.parametrize(
    "filename,content,max_bytes,expected",
    [
        ("prov.docx", b"paket", None, "Välj en .zip-fil med ett QTI-paket."),
        ("anteckningar.txt", b"paket", None, "Välj en .zip-fil med ett QTI-paket."),
        ("prov.zip", b"", None, "Filen saknar innehåll."),
        ("prov.zip", b"12345", 3, "Filen är större än maxstorleken för Mina filer."),
    ],
    ids=["docx", "txt", "empty", "oversized"],
)
@pytest.mark.asyncio
async def test_parse_rejects_invalid_uploads_with_the_swedish_error(
    filename, content, max_bytes, expected
):
    settings = _settings()
    if max_bytes is not None:
        settings = settings.model_copy(update={"VAULT_MAX_FILE_BYTES": max_bytes})
    handler = _parse_handler(settings)

    with pytest.raises(DomainError) as error:
        handler.handle(filename=filename, content=content, course_key=None)

    assert error.value.code is ErrorCode.VALIDATION_ERROR
    assert error.value.message == expected


@pytest.mark.asyncio
async def test_parse_rejects_a_filename_that_is_not_a_zip_with_the_filename_detail():
    handler = _parse_handler(_settings())

    with pytest.raises(DomainError) as error:
        handler.handle(filename="prov.docx", content=b"paket", course_key=None)

    assert error.value.details == {"filename": "prov.docx"}


@pytest.mark.asyncio
async def test_parse_rejects_an_unknown_course_key():
    handler = _parse_handler(_settings())

    with pytest.raises(DomainError) as error:
        handler.handle(filename="prov.zip", content=_package_bytes(), course_key="NOT-A-COURSE")

    assert error.value.code is ErrorCode.VALIDATION_ERROR
    assert error.value.message == "Välj en kurs ur kurslistan."
    assert error.value.details == {"field": "course_key"}


@pytest.mark.asyncio
async def test_parse_rejects_an_overlong_course_key():
    handler = _parse_handler(_settings())

    with pytest.raises(DomainError) as error:
        handler.handle(filename="prov.zip", content=_package_bytes(), course_key="X" * 65)

    assert error.value.message == "Kurskoden får vara högst 64 tecken."
    assert error.value.details == {"field": "course_key"}


@pytest.mark.asyncio
async def test_import_saves_revision_one_in_a_transaction_and_returns_its_summary():
    content = _package_bytes()
    settings = _settings()
    store, vault_files = _store(settings)
    handler = ImportExamWorkspaceQtiDocumentHandler(
        parse=_parse_handler(settings),
        store=store,
        codec=ExamWorkspaceContainerCodec(),
        id_generator=SequenceIdGenerator([uuid4() for _ in range(5)]),
    )
    actor = _actor()

    summary = await handler.handle(
        actor=actor, filename="prov.zip", content=content, course_key=_COURSE_KEY
    )

    files = list(vault_files.files.values())
    assert len(files) == 1
    vault_file = files[0]
    assert summary.vault_file_id == vault_file.id
    assert summary.lineage_id == vault_file.document_lineage_id
    assert summary.version == 1
    assert summary.name == "prov.provdokument.zip"
    assert summary.title == "prov"
    assert summary.course_key == _COURSE_KEY
    assert summary.saved_at == vault_file.document_saved_at


@pytest.mark.asyncio
async def test_import_writes_a_reopenable_revision_one_baseline():
    content = _package_bytes()
    settings = _settings()
    store, _vault_files = _store(settings)
    handler = ImportExamWorkspaceQtiDocumentHandler(
        parse=_parse_handler(settings),
        store=store,
        codec=ExamWorkspaceContainerCodec(),
        id_generator=SequenceIdGenerator([uuid4() for _ in range(5)]),
    )
    actor = _actor()

    summary = await handler.handle(
        actor=actor, filename="prov.zip", content=content, course_key=_COURSE_KEY
    )

    history = await store.get_history(actor=actor, lineage_id=summary.lineage_id)
    assert history.current_step_id == summary.lineage_id
    baseline_document = (
        ExamWorkspaceContainerCodec().parse(content=history.baseline.content).document
    )
    assert baseline_document.revision == 1
    assert baseline_document.origin.kind == "qti_import"


@pytest.mark.asyncio
async def test_import_refuses_the_same_invalid_uploads_the_parse_refuses():
    settings = _settings()
    store, vault_files = _store(settings)
    handler = ImportExamWorkspaceQtiDocumentHandler(
        parse=_parse_handler(settings),
        store=store,
        codec=ExamWorkspaceContainerCodec(),
        id_generator=SequenceIdGenerator([uuid4() for _ in range(5)]),
    )

    with pytest.raises(DomainError) as error:
        await handler.handle(
            actor=_actor(), filename="prov.docx", content=b"paket", course_key=None
        )

    assert error.value.message == "Välj en .zip-fil med ett QTI-paket."
    assert vault_files.files == {}
