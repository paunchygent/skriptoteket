"""Guard shared fake behavior that can otherwise hide vault rename regressions."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from skriptoteket.domain.scripting.vault import (
    VaultFile,
    VaultFileSourceKind,
    VaultListSort,
    VaultListState,
)
from tests.unit.application.curated_apps.handlers.vault_file_repository_test_support import (
    InMemoryVaultFileRepository,
)

_NOW = datetime(2026, 10, 16, tzinfo=UTC)
_OWNER = UUID(int=1)
_OTHER_OWNER = UUID(int=2)
_LINEAGE = UUID(int=3)
_OTHER_LINEAGE = UUID(int=4)


def _file(
    number: int,
    *,
    user_id: UUID = _OWNER,
    lineage_id: UUID | None = _LINEAGE,
    version: int = 1,
    deleted: bool = False,
    name: str = "Prov.provdokument.zip",
    export_format: str | None = None,
) -> VaultFile:
    return VaultFile(
        id=UUID(int=number),
        user_id=user_id,
        name=name,
        bytes=321,
        source_kind=VaultFileSourceKind.APP_EXPORT,
        source_artifact_id="exam-workspace:document",
        document_lineage_id=lineage_id,
        document_version=version,
        export_format=export_format,
        created_at=_NOW,
        deleted_at=_NOW if deleted else None,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("file", "exclude_lineage_id", "exclude_file_id", "expected"),
    [
        (_file(10), None, None, True),
        (_file(10, deleted=True), None, None, False),
        (_file(10, user_id=_OTHER_OWNER), None, None, False),
        (_file(10), _LINEAGE, None, False),
        (_file(10), _OTHER_LINEAGE, None, True),
        (_file(10, lineage_id=None), _LINEAGE, None, True),
        (_file(10), None, UUID(int=10), False),
        (_file(10), None, UUID(int=11), True),
        (_file(10, name="prov.provdokument.zip"), None, None, False),
    ],
    ids=[
        "active",
        "trash",
        "foreign",
        "own-lineage",
        "other-lineage",
        "unversioned",
        "own-file",
        "other-file",
        "exact-name",
    ],
)
async def test_name_in_use_obeys_owner_active_exact_name_and_exclusions(
    file: VaultFile,
    exclude_lineage_id: UUID | None,
    exclude_file_id: UUID | None,
    expected: bool,
) -> None:
    repo = InMemoryVaultFileRepository()
    repo.files[file.id] = file

    assert (
        await repo.name_in_use(
            user_id=_OWNER,
            name="Prov.provdokument.zip",
            exclude_lineage_id=exclude_lineage_id,
            exclude_file_id=exclude_file_id,
        )
        is expected
    )


@pytest.mark.asyncio
async def test_document_head_is_the_one_active_exam_row_excluding_exports_and_trash() -> None:
    repo = InMemoryVaultFileRepository()
    exam = _file(10)
    export = _file(11, export_format="qti")
    trashed = _file(12, deleted=True)
    other_lineage = _file(13, lineage_id=_OTHER_LINEAGE)
    foreign = _file(14, user_id=_OTHER_OWNER)
    repo.files = {file.id: file for file in (exam, export, trashed, other_lineage, foreign)}

    assert await repo.get_document_head(user_id=_OWNER, document_lineage_id=_LINEAGE) == exam
    assert (
        await repo.get_document_head(user_id=_OWNER, document_lineage_id=_OTHER_LINEAGE)
        == other_lineage
    )
    assert (
        await repo.get_document_head(user_id=_OTHER_OWNER, document_lineage_id=_LINEAGE) == foreign
    )
    assert await repo.get_document_head(user_id=_OWNER, document_lineage_id=UUID(int=99)) is None
    assert await repo.list_saved_exports(user_id=_OWNER, document_lineage_id=_LINEAGE) == [export]


@pytest.mark.asyncio
@pytest.mark.parametrize("state", ["active", "trash", "foreign", "missing"])
async def test_rename_active_changes_only_one_owned_active_record(state: str) -> None:
    repo = InMemoryVaultFileRepository()
    target = _file(
        10, deleted=state == "trash", user_id=_OTHER_OWNER if state == "foreign" else _OWNER
    )
    sibling = _file(11, version=2)
    repo.files = {sibling.id: sibling}
    if state != "missing":
        repo.files[target.id] = target
    before = dict(repo.files)

    result = await repo.rename_active(user_id=_OWNER, file_id=target.id, name="Nytt.zip")

    if state == "active":
        renamed = target.model_copy(update={"name": "Nytt.zip"})
        assert result == renamed
        assert repo.files == {**before, target.id: renamed}
    else:
        assert result is None
        assert repo.files == before


@pytest.mark.asyncio
async def test_rename_lineage_renames_the_exam_row_including_trash_but_not_exports() -> None:
    repo = InMemoryVaultFileRepository()
    exam = _file(10)
    trashed = _file(11, version=2, deleted=True)
    untouched = [
        _file(12, lineage_id=_OTHER_LINEAGE),
        _file(13, user_id=_OTHER_OWNER),
        _file(14, lineage_id=None),
        _file(15, export_format="qti"),
    ]
    repo.files = {file.id: file for file in (exam, trashed, *untouched)}

    result = await repo.rename_lineage(
        user_id=_OWNER, document_lineage_id=_LINEAGE, name="Nytt.zip"
    )

    renamed = [file.model_copy(update={"name": "Nytt.zip"}) for file in (exam, trashed)]
    assert {file.id: file for file in result} == {file.id: file for file in renamed}
    assert repo.files == {file.id: file for file in (*renamed, *untouched)}
    assert (
        await repo.rename_lineage(
            user_id=_OWNER, document_lineage_id=UUID(int=99), name="Missing.zip"
        )
        == []
    )


@pytest.mark.asyncio
async def test_owner_lock_records_identity_before_collision_read_without_mutating_files() -> None:
    repo = InMemoryVaultFileRepository()
    file = _file(10)
    repo.files[file.id] = file

    await repo.lock_owner_renames(user_id=_OWNER)
    await repo.name_in_use(
        user_id=_OWNER, name=file.name, exclude_lineage_id=None, exclude_file_id=None
    )

    assert repo.calls == [
        ("lock_owner_renames", {"user_id": _OWNER}),
        ("name_in_use", {"user_id": _OWNER, "name": file.name}),
    ]
    assert repo.files == {file.id: file}


@pytest.mark.asyncio
async def test_update_changes_only_lifecycle_state_and_keeps_a_concurrent_rename() -> None:
    repo = InMemoryVaultFileRepository()
    stale = _file(10)
    renamed = stale.model_copy(update={"name": "Nytt.zip"})
    repo.files[stale.id] = renamed

    deleted = await repo.update(file=stale.model_copy(update={"deleted_at": _NOW}))

    assert deleted == renamed.model_copy(update={"deleted_at": _NOW})
    assert repo.files == {stale.id: deleted}
    restored = await repo.update(file=stale)
    assert restored == renamed
    missing = _file(99)
    assert await repo.update(file=missing) == missing
    assert missing.id not in repo.files


@pytest.mark.asyncio
async def test_overwrite_writes_the_full_row_it_is_given_and_ignores_a_missing_row() -> None:
    repo = InMemoryVaultFileRepository()
    stored = _file(10)
    repo.files[stored.id] = stored

    overwritten = stored.model_copy(
        update={"name": "Nytt.zip", "bytes": 999, "document_version": 4}
    )

    assert await repo.overwrite(file=overwritten) == overwritten
    assert repo.files == {stored.id: overwritten}
    missing = _file(99)
    assert await repo.overwrite(file=missing) == missing
    assert missing.id not in repo.files


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("state", "search", "sort", "offset", "limit", "expected"),
    [
        (VaultListState.ACTIVE, "PROV", VaultListSort.NAME, 1, 1, [12]),
        (VaultListState.ACTIVE, None, VaultListSort.SIZE, 0, 2, [11, 13]),
        (VaultListState.ACTIVE, "", VaultListSort.NEWEST, 0, 2, [13, 12]),
        (VaultListState.TRASH, "prov", VaultListSort.NAME, 0, 10, [14]),
        (VaultListState.ACTIVE, "Prov_1", VaultListSort.NAME, 0, 10, [10, 12, 11]),
        (VaultListState.ACTIVE, r"Prov\_1", VaultListSort.NAME, 0, 10, [10, 12]),
        (VaultListState.ACTIVE, "Prov%", VaultListSort.NAME, 0, 10, [10, 12, 11]),
        (VaultListState.ACTIVE, None, VaultListSort.NAME, 99, 10, []),
    ],
    ids=[
        "name-page",
        "size-tie",
        "newest-tie",
        "trash",
        "wildcard-one",
        "escaped-wildcard",
        "wildcard-many",
        "past-last-page",
    ],
)
async def test_list_for_user_filters_orders_and_pages_like_the_repository(
    state: VaultListState,
    search: str | None,
    sort: VaultListSort,
    offset: int,
    limit: int,
    expected: list[int],
) -> None:
    repo = InMemoryVaultFileRepository()
    files = [
        _file(12, name="prov_1.zip"),
        _file(10, name="Prov_1.zip"),
        _file(11, name="ProvA1.zip").model_copy(update={"bytes": 900}),
        _file(13, name="Annat.zip").model_copy(update={"created_at": _NOW + timedelta(seconds=1)}),
        _file(14, deleted=True),
        _file(15, user_id=_OTHER_OWNER),
    ]
    repo.files = {file.id: file for file in files}

    result = await repo.list_for_user(
        user_id=_OWNER, state=state, search=search, sort=sort, limit=limit, offset=offset
    )

    assert [file.id for file in result] == [UUID(int=number) for number in expected]


@pytest.mark.asyncio
async def test_list_expired_uses_strict_cutoff_and_orders_oldest_then_id_before_limit() -> None:
    repo = InMemoryVaultFileRepository()
    old = _NOW - timedelta(days=2)
    files = [
        _file(12, deleted=True).model_copy(update={"deleted_at": old}),
        _file(11, deleted=True).model_copy(update={"deleted_at": old}),
        _file(10, deleted=True).model_copy(update={"deleted_at": _NOW - timedelta(days=1)}),
        _file(13, deleted=True),
        _file(14, deleted=True).model_copy(update={"deleted_at": _NOW + timedelta(seconds=1)}),
        _file(15),
    ]
    repo.files = {file.id: file for file in files}

    assert await repo.list_expired(cutoff=_NOW, limit=2) == [files[1], files[0]]
    assert await repo.list_expired(cutoff=_NOW, limit=10) == [files[1], files[0], files[2]]


@pytest.mark.asyncio
async def test_lineage_lock_records_identity_before_head_read_without_mutating_files() -> None:
    repo = InMemoryVaultFileRepository()
    file = _file(10)
    repo.files[file.id] = file

    await repo.lock_document_lineage(user_id=_OWNER, document_lineage_id=_LINEAGE)
    await repo.get_document_head(user_id=_OWNER, document_lineage_id=_LINEAGE)

    assert repo.calls == [
        ("lock_document_lineage", {"user_id": _OWNER, "document_lineage_id": _LINEAGE}),
        ("get_document_head", {"user_id": _OWNER, "document_lineage_id": _LINEAGE}),
    ]
    assert repo.files == {file.id: file}
