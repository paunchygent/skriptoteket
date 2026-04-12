from __future__ import annotations

from datetime import datetime
from typing import Generic, TypeVar
from uuid import UUID

from skriptoteket.domain.curated_apps.models import CuratedAppDefinition
from skriptoteket.domain.curated_apps.reagent_prep_chef.models import SdsCorpusEntry
from skriptoteket.domain.errors import not_found
from skriptoteket.domain.identity.models import User
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.curated_apps import CuratedAppRegistryProtocol
from skriptoteket.protocols.reagent_prep_chef import ReagentPrepChefSdsStoreProtocol

TResult = TypeVar("TResult")
TCommand = TypeVar("TCommand")


class FixedClock(ClockProtocol):
    def __init__(self, now: datetime) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now


class StubCuratedAppRegistry(CuratedAppRegistryProtocol):
    def __init__(self, *, app: CuratedAppDefinition) -> None:
        self._app = app

    def list_all(self) -> list[CuratedAppDefinition]:
        return [self._app]

    def get_by_app_id(self, *, app_id: str) -> CuratedAppDefinition | None:
        return self._app if self._app.app_id == app_id else None

    def get_by_tool_id(self, *, tool_id: UUID) -> CuratedAppDefinition | None:
        return self._app if self._app.tool_id == tool_id else None


class StubActorHandler(Generic[TResult]):
    def __init__(self) -> None:
        self.result: TResult | None = None
        self.calls: list[User] = []

    def set_result(self, result: TResult) -> None:
        self.result = result

    async def handle(self, *, actor: User) -> TResult:
        self.calls.append(actor)
        if self.result is None:
            raise AssertionError("StubActorHandler.result must be set before calling handle().")
        return self.result


class StubActorCommandHandler(Generic[TCommand, TResult]):
    def __init__(self) -> None:
        self.result: TResult | None = None
        self.calls: list[tuple[User, TCommand]] = []

    def set_result(self, result: TResult) -> None:
        self.result = result

    async def handle(self, *, actor: User, command: TCommand, **_: object) -> TResult:
        self.calls.append((actor, command))
        if self.result is None:
            raise AssertionError(
                "StubActorCommandHandler.result must be set before calling handle()."
            )
        return self.result


class StubSdsStore(ReagentPrepChefSdsStoreProtocol):
    def __init__(self) -> None:
        self._entries: dict[str, SdsCorpusEntry] = {}
        self._markdown: dict[str, str] = {}
        self._pdf: dict[str, tuple[str, bytes, str]] = {}
        self.calls_entry: list[str] = []
        self.calls_markdown: list[str] = []
        self.calls_pdf: list[str] = []

    def add(
        self,
        *,
        sds_ref: str,
        key: str | None = None,
        md_file_name: str = "sds.md",
        provider: str = "test",
        revision: str = "undated",
        markdown: str | None = None,
        pdf_file_name: str | None = None,
        pdf_bytes: bytes | None = None,
        pdf_media_type: str = "application/pdf",
    ) -> None:
        entry = SdsCorpusEntry(
            sds_ref=sds_ref,
            key=key or sds_ref,
            md_file_name=md_file_name,
            provider=provider,
            revision=revision,
            pdf_file_name=pdf_file_name,
        )
        self._entries[sds_ref] = entry
        if markdown is not None:
            self._markdown[sds_ref] = markdown
        if pdf_bytes is not None and pdf_file_name is not None:
            self._pdf[sds_ref] = (pdf_file_name, pdf_bytes, pdf_media_type)

    def get_entry(self, *, sds_ref: str) -> SdsCorpusEntry:
        self.calls_entry.append(sds_ref)
        entry = self._entries.get(sds_ref)
        if entry is None:
            raise not_found("SDS", sds_ref)
        return entry

    def get_markdown(self, *, sds_ref: str) -> tuple[SdsCorpusEntry, str]:
        self.calls_markdown.append(sds_ref)
        entry = self.get_entry(sds_ref=sds_ref)
        markdown = self._markdown.get(sds_ref)
        if markdown is None:
            raise not_found("SDS", sds_ref)
        return (entry, markdown)

    def get_pdf(self, *, sds_ref: str) -> tuple[str, bytes, str]:
        self.calls_pdf.append(sds_ref)
        stored = self._pdf.get(sds_ref)
        if stored is None:
            raise not_found("SDS", sds_ref)
        return stored
