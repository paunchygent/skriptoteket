"""Public guest QTI start: a packaged upload parses with no stored exam.

These tests run the real FastAPI router and prove a guest .zip parses through
the stateless 41-02-01 parse handler into a document plus its picture bytes,
with no vault, store or Unit of Work anywhere in the test container: if the
route needed Mina filer, Dishka would fail to build it. A refused admission
returns 429 without parsing, and the parser's own validation errors reach HTTP.
"""

from __future__ import annotations

import base64
import hashlib
from collections.abc import AsyncIterator
from uuid import uuid4

import httpx
import pytest
from dishka import Provider, Scope, make_async_container, provide
from fastapi import FastAPI
from starlette_dishka import setup_dishka

from skriptoteket.application.curated_apps.exam_workspace_exports import (
    build_native_examnet_qti_package,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_misspellings import (
    GenerateExamWorkspaceMisspellingsHandler,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_qti_import import (
    ParseExamWorkspaceQtiPackageHandler,
)
from skriptoteket.application.curated_apps.handlers.public_exam_workspace_commands import (
    PublicExamWorkspaceCommandHandler,
)
from skriptoteket.config import Settings
from skriptoteket.domain.curated_apps.exam_workspace.container import (
    ExamWorkspaceContainerContent,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeAssetSegment,
    NativeParagraph,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamAsset,
    NativeExamDocument,
    NativeExamDocumentOrigin,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.examnet_qti_package_reader import (  # noqa: E501
    ExamNetQtiPackageReader,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.examnet_qti_writer import (
    ExamNetQtiPackageWriter,
)
from skriptoteket.protocols.curated_apps import CuratedAppRegistryProtocol
from skriptoteket.protocols.exam_workspace import (
    GenerateExamWorkspaceMisspellingsHandlerProtocol,
    ParseExamWorkspaceQtiPackageHandlerProtocol,
)
from skriptoteket.protocols.public_request_limits import (
    AdmitPublicRequestHandlerProtocol,
    PublicRequestBucket,
    PublicRequestRefusal,
)
from skriptoteket.web.api.v1 import public_apps_exam_workspace_commands as commands_api
from skriptoteket.web.middleware.error_handler import error_handler_middleware
from tests.unit.application.curated_apps.handlers.test_conversion_hub_jobs import (
    SequenceIdGenerator,
)
from tests.unit.domain.curated_apps.exam_workspace.native_exam_test_builders import (
    make_free_text_item,
    make_gap_fill_item,
    make_single_choice_item,
)
from tests.unit.web import (
    public_exam_workspace_command_routes_test_support as route_support,
)
from tests.unit.web.public_exam_workspace_command_routes_test_support import (
    _BASE,
    FakeAdmitHandler,
)

admit = route_support.admit
registry = route_support.registry

_PICTURE = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000080000000408020000004df026"
    "7a0000000c49444154789c6360606060000004c0001a37ced8e9000000004945"
    "4e44ae426082"
)
_PICTURE_ASSET_ID = "asset_0123456789abcdef"


class RecordingParseHandler:
    """A parse double that returns a fixed container and records every call."""

    def __init__(self, container: ExamWorkspaceContainerContent) -> None:
        self.calls: list[dict[str, object]] = []
        self.container = container

    def handle(
        self, *, filename: str, content: bytes, course_key: str | None
    ) -> ExamWorkspaceContainerContent:
        self.calls.append({"content": content, "course_key": course_key, "filename": filename})
        return self.container


def _real_parse_handler() -> ParseExamWorkspaceQtiPackageHandlerProtocol:
    return ParseExamWorkspaceQtiPackageHandler(
        reader=ExamNetQtiPackageReader(),
        settings=Settings(),
        id_generator=SequenceIdGenerator([uuid4() for _ in range(8)]),
    )


class GuestQtiImportProvider(Provider):
    """The public command router plus the QTI parse lane under test."""

    def __init__(
        self,
        *,
        registry: CuratedAppRegistryProtocol,
        admit: AdmitPublicRequestHandlerProtocol,
        parse: ParseExamWorkspaceQtiPackageHandlerProtocol,
    ) -> None:
        super().__init__()
        self._registry = registry
        self._admit = admit
        self._parse = parse

    @provide(scope=Scope.APP)
    def settings(self) -> Settings:
        return Settings()

    @provide(scope=Scope.APP)
    def registry(self) -> CuratedAppRegistryProtocol:
        return self._registry

    @provide(scope=Scope.APP)
    def admit_handler(self) -> AdmitPublicRequestHandlerProtocol:
        return self._admit

    @provide(scope=Scope.APP)
    def parse_handler(self) -> ParseExamWorkspaceQtiPackageHandlerProtocol:
        return self._parse

    @provide(scope=Scope.APP)
    def command_handler(self) -> PublicExamWorkspaceCommandHandler:
        import random

        return PublicExamWorkspaceCommandHandler(rng=random.Random(1))

    @provide(scope=Scope.APP)
    def misspellings_handler(self) -> GenerateExamWorkspaceMisspellingsHandlerProtocol:
        return GenerateExamWorkspaceMisspellingsHandler()


def _picture_document() -> NativeExamDocument:
    digest = hashlib.sha256(_PICTURE).hexdigest()
    return NativeExamDocument(
        document_id=uuid4(),
        revision=1,
        title="Bildprov",
        items=(make_free_text_item(sequence=1, item_id="item_001"),),
        parents=(),
        instructions=(
            NativeParagraph(
                heading_level=None,
                segments=(NativeAssetSegment(asset_id=_PICTURE_ASSET_ID),),
            ),
        ),
        assets=(
            NativeExamAsset(
                asset_id=_PICTURE_ASSET_ID,
                sha256=digest,
                media_type="image/png",
                byte_length=len(_PICTURE),
                width=8,
                height=4,
            ),
        ),
        origin=NativeExamDocumentOrigin(
            kind="qti_import", source_filename="prov.zip", source_sha256=digest
        ),
    )


def _picture_container() -> ExamWorkspaceContainerContent:
    return ExamWorkspaceContainerContent(
        document=_picture_document(), assets_by_id={_PICTURE_ASSET_ID: _PICTURE}
    )


def _package_bytes() -> bytes:
    """A real exported package: one choice question and one gap-fill question."""
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


def _mount(
    *,
    registry: CuratedAppRegistryProtocol,
    admit: AdmitPublicRequestHandlerProtocol,
    parse: ParseExamWorkspaceQtiPackageHandlerProtocol,
) -> FastAPI:
    app = FastAPI()
    app.middleware("http")(error_handler_middleware)
    app.include_router(commands_api.router)
    container = make_async_container(
        GuestQtiImportProvider(registry=registry, admit=admit, parse=parse)
    )
    setup_dishka(container, app)
    return app


@pytest.fixture
async def client(
    registry: CuratedAppRegistryProtocol, admit: FakeAdmitHandler
) -> AsyncIterator[httpx.AsyncClient]:
    app = _mount(registry=registry, admit=admit, parse=_real_parse_handler())
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client


async def test_valid_package_returns_document_with_assets_and_no_stored_exam(
    client: httpx.AsyncClient, admit: FakeAdmitHandler
) -> None:
    response = await client.post(
        f"{_BASE}/imports/qti",
        files={"file": ("prov.zip", _package_bytes(), "application/zip")},
        data={"course_key": "SVESVE02"},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["document"]["origin"]["kind"] == "qti_import"
    assert body["document"]["origin"]["source_filename"] == "prov.zip"
    assert body["document"]["header"]["course"]["key"] == "SVESVE02"
    assert len(body["document"]["items"]) == 2
    assert body["assets_by_id"] == {}
    assert isinstance(body["notes"], list)
    assert admit.calls == [(PublicRequestBucket.GUEST_IMPORT, "127.0.0.1")]


async def test_picture_assets_return_as_base64_decoding_to_source_bytes(
    registry: CuratedAppRegistryProtocol, admit: FakeAdmitHandler
) -> None:
    parse = RecordingParseHandler(_picture_container())
    app = _mount(registry=registry, admit=admit, parse=parse)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            f"{_BASE}/imports/qti",
            files={"file": ("prov.zip", b"package-bytes", "application/zip")},
        )

    assert response.status_code == 200, response.text
    body = response.json()
    assert [asset["asset_id"] for asset in body["document"]["assets"]] == [_PICTURE_ASSET_ID]
    assert base64.b64decode(body["assets_by_id"][_PICTURE_ASSET_ID]) == _PICTURE
    assert parse.calls == [
        {
            "content": b"package-bytes",
            "course_key": None,
            "filename": "prov.zip",
        }
    ]


@pytest.mark.parametrize(
    "refusal", [PublicRequestRefusal.CALLER_LIMIT, PublicRequestRefusal.POOL_LIMIT]
)
async def test_refused_admission_returns_429_and_never_parses(
    registry: CuratedAppRegistryProtocol,
    admit: FakeAdmitHandler,
    refusal: PublicRequestRefusal,
) -> None:
    admit.refusal = refusal
    parse = RecordingParseHandler(_picture_container())
    app = _mount(registry=registry, admit=admit, parse=parse)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            f"{_BASE}/imports/qti",
            files={"file": ("prov.zip", b"package-bytes", "application/zip")},
        )

    assert response.status_code == 429
    assert response.json()["error"]["details"] == {
        "reason": refusal.value,
        "bucket": PublicRequestBucket.GUEST_IMPORT.value,
    }
    assert parse.calls == []


async def test_non_zip_upload_gets_parser_validation_error(
    client: httpx.AsyncClient,
) -> None:
    response = await client.post(
        f"{_BASE}/imports/qti",
        files={"file": ("anteckningar.txt", b"not a zip", "text/plain")},
    )

    assert response.status_code == 422, response.text
    assert "Välj en .zip-fil med ett QTI-paket." in response.text


async def test_empty_upload_gets_parser_validation_error(
    client: httpx.AsyncClient,
) -> None:
    response = await client.post(
        f"{_BASE}/imports/qti",
        files={"file": ("prov.zip", b"", "application/zip")},
    )

    assert response.status_code == 422, response.text
    assert "Filen saknar innehåll." in response.text
