from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from skriptoteket.domain.identity.models import AuthProvider, Role
from skriptoteket.domain.scripting.vault import VaultFile, VaultFileSourceKind
from skriptoteket.infrastructure.db.models.user import UserModel
from skriptoteket.infrastructure.repositories.user_vault_file_repository import (
    PostgreSQLUserVaultFileRepository,
)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.docker,
    pytest.mark.asyncio(loop_scope="module"),
]
_NOW = datetime(2026, 10, 16, tzinfo=UTC)


async def _owner(session: AsyncSession) -> UUID:
    user_id = uuid4()
    session.add(
        UserModel(
            id=user_id,
            email=f"rename-{user_id}@example.com",
            password_hash="hash",
            role=Role.USER,
            auth_provider=AuthProvider.LOCAL,
            created_at=_NOW,
            updated_at=_NOW,
        )
    )
    await session.flush()
    return user_id


def _file(user_id: UUID, **updates: object) -> VaultFile:
    return VaultFile(
        id=uuid4(),
        user_id=user_id,
        name="Prov.pdf",
        bytes=42,
        source_kind=VaultFileSourceKind.APP_EXPORT,
        created_at=_NOW,
    ).model_copy(update=updates)


async def test_collision_query_handles_null_lineages_owner_trash_and_each_exclusion(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        repo = PostgreSQLUserVaultFileRepository(session)
        owner = await _owner(session)
        other_owner = await _owner(session)
        lineage = uuid4()
        own = _file(owner, name="Eget.pdf", document_lineage_id=lineage, document_version=1)
        plain = _file(owner, name="Upptaget.pdf")
        for file in [
            own,
            plain,
            _file(owner, name="Papperskorg.pdf", deleted_at=_NOW),
            _file(other_owner, name="Annan.pdf"),
        ]:
            await repo.create(file=file)
        # Excluding a lineage must retain unrelated NULL-lineage records (SQL three-valued logic).
        assert await repo.name_in_use(
            user_id=owner,
            name=plain.name,
            exclude_lineage_id=lineage,
            exclude_file_id=own.id,
        )
        for name in ("Eget.pdf", "Papperskorg.pdf", "Annan.pdf", "Saknas.pdf"):
            assert not await repo.name_in_use(
                user_id=owner,
                name=name,
                exclude_lineage_id=lineage,
                exclude_file_id=own.id,
            )
        assert await repo.name_in_use(
            user_id=owner,
            name=own.name,
            exclude_lineage_id=None,
            exclude_file_id=None,
        )
        assert not await repo.name_in_use(
            user_id=owner,
            name=plain.name,
            exclude_lineage_id=None,
            exclude_file_id=plain.id,
        )
        await session.rollback()


async def test_lineage_query_includes_trashed_versions_but_not_other_owners_or_lineages(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        repo = PostgreSQLUserVaultFileRepository(session)
        owner = await _owner(session)
        other_owner = await _owner(session)
        lineage = uuid4()
        versions = [
            _file(
                owner,
                document_lineage_id=lineage,
                document_version=version,
                deleted_at=_NOW if version == 2 else None,
            )
            for version in (1, 2, 3)
        ]
        for file in [
            *versions,
            _file(owner, document_lineage_id=uuid4(), document_version=1),
            _file(other_owner, document_lineage_id=lineage, document_version=4),
            _file(owner),
        ]:
            await repo.create(file=file)
        actual = await repo.list_lineage_versions(user_id=owner, document_lineage_id=lineage)
        assert {file.id: file for file in actual} == {file.id: file for file in versions}
        assert await repo.list_lineage_versions(user_id=owner, document_lineage_id=uuid4()) == []
        await session.rollback()
