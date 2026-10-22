"""Autosave carries a new picture's bytes once; the server checks and stores them."""

import hashlib
import json
from pathlib import Path
from typing import Literal
from uuid import UUID, uuid4

import pytest

from skriptoteket.application.curated_apps.exam_workspace_history import (
    StoreExamWorkspaceUndoStepRequest,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_document_store import (
    ExamWorkspaceDocumentStore,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_undo_steps import (
    StoreExamWorkspaceUndoStepHandler,
)
from skriptoteket.config import Settings
from skriptoteket.domain.curated_apps.exam_workspace.container import ExamWorkspaceContainerContent
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamAsset,
    NativeExamDocument,
)
from skriptoteket.domain.errors import DomainError
from skriptoteket.domain.identity.models import User
from tests.fixtures.time_fixtures import FixedClock
from tests.unit.application.curated_apps.handlers.test_conversion_hub_jobs import (
    SequenceIdGenerator,
)
from tests.unit.application.curated_apps.handlers.test_exam_workspace_documents import (
    _NOW,
    FakeUow,
    _actor,
    _Env,
    _leased_tab,
)
from tests.unit.application.curated_apps.handlers.test_exam_workspace_history_contract import (
    _handler,
    _undo_handler,
)
from tests.unit.application.curated_apps.handlers.test_exam_workspace_step_storage import (
    _pictured,
)

_PNG = b"\x89PNG\r\n\x1a\n" + bytes(100)
_JPEG = b"\xff\xd8\xff" + bytes(100)
_FIXTURE = Path("tests/fixtures/exam_conversion/native_workspace_grammatik.json")


def _declared_asset(
    payload: bytes, media_type: Literal["image/png", "image/jpeg"]
) -> NativeExamAsset:
    digest = hashlib.sha256(payload).hexdigest()
    return NativeExamAsset(
        asset_id=f"asset_{digest[:16]}",
        sha256=digest,
        media_type=media_type,
        byte_length=len(payload),
    )


async def _seed(env: _Env, actor: User) -> tuple[UUID, NativeExamDocument]:
    imported = await env.seed_document(actor=actor)
    return imported.summary.lineage_id, imported.document


async def _store(
    env: _Env,
    actor: User,
    lineage: UUID,
    document: NativeExamDocument,
    new_assets_by_id: dict[str, bytes] | None = None,
    store: ExamWorkspaceDocumentStore | None = None,
) -> UUID:
    cursor = (await _handler(env).history(actor=actor, lineage_id=lineage)).cursor
    handler = _undo_handler(env) if store is None else _undo_handler_with_store(env, store)
    response = await handler.handle(
        actor=actor,
        lineage_id=lineage,
        request=StoreExamWorkspaceUndoStepRequest(
            expected_cursor=cursor,
            document=document,
            tab_id=await _leased_tab(env, actor, lineage),
            new_assets_by_id=dict(new_assets_by_id or {}),
        ),
    )
    return response.history.position_step_id


def _undo_handler_with_store(
    env: _Env, store: ExamWorkspaceDocumentStore
) -> StoreExamWorkspaceUndoStepHandler:
    return StoreExamWorkspaceUndoStepHandler(
        clock=FixedClock(_NOW),
        vault_files=env.vault_files,
        codec=env.codec,
        store=store,
        id_generator=SequenceIdGenerator([uuid4() for _ in range(100)]),
        jobs=env.enrichment_jobs,
    )


async def _file_content(env: _Env, actor: User, lineage: UUID) -> bytes:
    head = next(
        file
        for file in env.vault_files.files.values()
        if file.document_lineage_id == lineage and file.export_format is None
    )
    return await env.store.load(actor=actor, vault_file=head)


async def _history_ids(env: _Env, actor: User, lineage: UUID) -> tuple[UUID, tuple[UUID, ...]]:
    history = await _handler(env).history(actor=actor, lineage_id=lineage)
    return history.cursor, history.step_ids


@pytest.mark.asyncio
async def test_first_autosave_with_new_picture_bytes_stores_the_step_and_the_file() -> None:
    env = _Env()
    actor = _actor()
    lineage, plain = await _seed(env, actor)
    asset = _declared_asset(_PNG, "image/png")
    pictured = _pictured(plain, asset)

    await _store(env, actor, lineage, pictured, {asset.asset_id: _PNG})

    stored = env.codec.parse(content=await _file_content(env, actor, lineage))
    assert stored.document.assets == (asset,)
    assert stored.assets_by_id == {asset.asset_id: _PNG}
    assert env.vault_files.history_assets[(actor.id, lineage, asset.asset_id)] == _PNG


@pytest.mark.asyncio
async def test_second_autosave_without_bytes_finds_the_picture_again() -> None:
    env = _Env()
    actor = _actor()
    lineage, plain = await _seed(env, actor)
    asset = _declared_asset(_PNG, "image/png")
    pictured = _pictured(plain, asset)
    await _store(env, actor, lineage, pictured, {asset.asset_id: _PNG})

    await _store(env, actor, lineage, pictured.model_copy(update={"title": "Text senare"}))

    stored = env.codec.parse(content=await _file_content(env, actor, lineage))
    assert stored.document.title == "Text senare"
    assert stored.assets_by_id == {asset.asset_id: _PNG}


@pytest.mark.asyncio
async def test_first_autosave_without_bytes_is_refused_as_missing() -> None:
    env = _Env()
    actor = _actor()
    lineage, plain = await _seed(env, actor)
    pictured = _pictured(plain, _declared_asset(_PNG, "image/png"))
    history_before = await _history_ids(env, actor, lineage)
    file_before = await _file_content(env, actor, lineage)

    with pytest.raises(DomainError) as error:
        await _store(env, actor, lineage, pictured)

    assert error.value.message == "Dokumentet hänvisar till bilder som saknas."
    assert await _history_ids(env, actor, lineage) == history_before
    assert await _file_content(env, actor, lineage) == file_before


@pytest.mark.asyncio
async def test_digest_mismatch_is_refused_and_stores_nothing() -> None:
    env = _Env()
    actor = _actor()
    lineage, plain = await _seed(env, actor)
    asset = _declared_asset(_PNG, "image/png")
    pictured = _pictured(plain, asset)
    tampered = _PNG[:8] + b"\x01" * 100
    assert len(tampered) == len(_PNG)
    assert hashlib.sha256(tampered).hexdigest() != asset.sha256
    history_before = await _history_ids(env, actor, lineage)
    file_before = await _file_content(env, actor, lineage)

    with pytest.raises(DomainError) as error:
        await _store(env, actor, lineage, pictured, {asset.asset_id: tampered})

    assert error.value.message == "Bilden kunde inte sparas."
    assert error.value.details == {"asset_id": asset.asset_id}
    assert await _history_ids(env, actor, lineage) == history_before
    assert await _file_content(env, actor, lineage) == file_before


@pytest.mark.asyncio
async def test_byte_length_mismatch_is_refused_and_stores_nothing() -> None:
    env = _Env()
    actor = _actor()
    lineage, plain = await _seed(env, actor)
    digest = hashlib.sha256(_PNG).hexdigest()
    asset = NativeExamAsset(
        asset_id=f"asset_{digest[:16]}",
        sha256=digest,
        media_type="image/png",
        byte_length=len(_PNG) + 1,
    )
    pictured = _pictured(plain, asset)
    history_before = await _history_ids(env, actor, lineage)
    file_before = await _file_content(env, actor, lineage)

    with pytest.raises(DomainError) as error:
        await _store(env, actor, lineage, pictured, {asset.asset_id: _PNG})

    assert error.value.message == "Bilden kunde inte sparas."
    assert await _history_ids(env, actor, lineage) == history_before
    assert await _file_content(env, actor, lineage) == file_before


@pytest.mark.asyncio
async def test_wrong_signature_is_refused_and_stores_nothing() -> None:
    env = _Env()
    actor = _actor()
    lineage, plain = await _seed(env, actor)
    asset = _declared_asset(_JPEG, "image/png")
    pictured = _pictured(plain, asset)
    history_before = await _history_ids(env, actor, lineage)
    file_before = await _file_content(env, actor, lineage)

    with pytest.raises(DomainError) as error:
        await _store(env, actor, lineage, pictured, {asset.asset_id: _JPEG})

    assert error.value.message == "Bilden kunde inte sparas."
    assert await _history_ids(env, actor, lineage) == history_before
    assert await _file_content(env, actor, lineage) == file_before


@pytest.mark.asyncio
async def test_undeclared_id_is_refused_and_stores_nothing() -> None:
    env = _Env()
    actor = _actor()
    lineage, plain = await _seed(env, actor)
    asset = _declared_asset(_PNG, "image/png")
    history_before = await _history_ids(env, actor, lineage)
    file_before = await _file_content(env, actor, lineage)

    with pytest.raises(DomainError) as error:
        await _store(env, actor, lineage, plain, {asset.asset_id: _PNG})

    assert error.value.message == "Bilden kunde inte sparas."
    assert await _history_ids(env, actor, lineage) == history_before
    assert await _file_content(env, actor, lineage) == file_before


@pytest.mark.asyncio
async def test_oversize_picture_is_refused_by_the_size_check() -> None:
    env = _Env()
    actor = _actor()
    lineage, plain = await _seed(env, actor)
    asset = _declared_asset(_PNG, "image/png")
    pictured = _pictured(plain, asset)
    pictured_content = env.codec.build(
        content=ExamWorkspaceContainerContent(
            document=pictured.model_copy(update={"revision": 2}),
            assets_by_id={asset.asset_id: _PNG},
        )
    )
    small_store = ExamWorkspaceDocumentStore(
        vault_files=env.vault_files,
        vault_usage=env.vault_usage,
        vault_storage=env.vault_storage,
        uow=FakeUow(),
        clock=FixedClock(_NOW),
        settings=Settings.model_construct(
            VAULT_MAX_FILE_BYTES=len(pictured_content) - 1,
            VAULT_MAX_TOTAL_BYTES=50_000_000,
        ),
        index=env.index,
        codec=env.codec,
    )
    history_before = await _history_ids(env, actor, lineage)
    file_before = await _file_content(env, actor, lineage)

    with pytest.raises(DomainError) as error:
        await _store(env, actor, lineage, pictured, {asset.asset_id: _PNG}, store=small_store)

    assert error.value.message == "Dokumentets storlek är inte tillåten."
    assert await _history_ids(env, actor, lineage) == history_before
    assert await _file_content(env, actor, lineage) == file_before


def test_request_model_round_trips_base64_json() -> None:
    document = NativeExamDocument.model_validate_json(_FIXTURE.read_bytes())
    request = StoreExamWorkspaceUndoStepRequest(
        expected_cursor=uuid4(),
        document=document,
        tab_id=uuid4(),
        new_assets_by_id={_declared_asset(_PNG, "image/png").asset_id: _PNG},
    )

    raw = json.loads(request.model_dump_json())
    asset_id = next(iter(request.new_assets_by_id))

    assert isinstance(raw["new_assets_by_id"][asset_id], str)
    assert (
        StoreExamWorkspaceUndoStepRequest.model_validate_json(
            request.model_dump_json()
        ).new_assets_by_id
        == request.new_assets_by_id
    )
