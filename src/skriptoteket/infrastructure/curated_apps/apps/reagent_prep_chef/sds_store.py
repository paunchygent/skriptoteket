"""Repo-owned SDS corpus store for Reagent Prep Chef.

ADR-0067: SDS is a markdown-first offline corpus:
- Markdown is committed under `data/reagent_prep_chef/sds/markdown/`
- Index is committed under `data/reagent_prep_chef/sds/index.json`
- PDFs are optional and provisioned outside git under `data/reagent_prep_chef/sds/files/`

The backend must not fetch SDS content at runtime; it only serves corpus files.
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from skriptoteket.domain.curated_apps.reagent_prep_chef.models import SdsCorpusEntry
from skriptoteket.domain.errors import not_found, validation_error
from skriptoteket.protocols.reagent_prep_chef import ReagentPrepChefSdsStoreProtocol


class _SdsIndexEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str
    display_name: str
    sds_ref: str
    md_file_name: str
    provider: str
    revision: str
    pdf_file_name: str | None = None

    def to_domain(self) -> SdsCorpusEntry:
        return SdsCorpusEntry(
            sds_ref=self.sds_ref,
            key=self.key,
            md_file_name=self.md_file_name,
            provider=self.provider,
            revision=self.revision,
            pdf_file_name=self.pdf_file_name,
        )


class _SdsIndex(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int = 1
    as_of: str
    entries: dict[str, _SdsIndexEntry] = Field(default_factory=dict)


class FileSystemReagentPrepChefSdsStore(ReagentPrepChefSdsStoreProtocol):
    def __init__(
        self,
        *,
        index_path: Path,
        markdown_dir: Path,
        pdf_dir: Path,
    ) -> None:
        self._index_path = index_path
        self._markdown_dir = markdown_dir
        self._pdf_dir = pdf_dir

        self._index = self._load_index(index_path=index_path)
        self._entries_by_ref: dict[str, _SdsIndexEntry] = {
            entry.sds_ref: entry for entry in self._index.entries.values()
        }

    def get_entry(self, *, sds_ref: str) -> SdsCorpusEntry:
        entry = self._lookup(sds_ref=sds_ref)
        return entry.to_domain()

    def get_markdown(self, *, sds_ref: str) -> tuple[SdsCorpusEntry, str]:
        entry = self._lookup(sds_ref=sds_ref)
        path = self._markdown_dir / entry.md_file_name
        if not path.is_file():
            raise not_found("SDS", sds_ref)
        return (entry.to_domain(), path.read_text(encoding="utf-8"))

    def get_pdf(self, *, sds_ref: str) -> tuple[str, bytes, str]:
        entry = self._lookup(sds_ref=sds_ref)
        if not entry.pdf_file_name:
            raise not_found("SDS", sds_ref)
        path = self._pdf_dir / entry.pdf_file_name
        if not path.is_file():
            raise not_found("SDS", sds_ref)
        return (entry.pdf_file_name, path.read_bytes(), "application/pdf")

    def _lookup(self, *, sds_ref: str) -> _SdsIndexEntry:
        normalized = sds_ref.strip()
        if not normalized:
            raise not_found("SDS", sds_ref)

        entry = self._index.entries.get(normalized) or self._entries_by_ref.get(normalized)
        if entry is None:
            raise not_found("SDS", sds_ref)
        return entry

    @staticmethod
    def _load_index(*, index_path: Path) -> _SdsIndex:
        try:
            payload = json.loads(index_path.read_text(encoding="utf-8"))
            return _SdsIndex.model_validate(payload)
        except FileNotFoundError as exc:
            raise not_found("SDS index", str(index_path)) from exc
        except (OSError, json.JSONDecodeError, ValidationError) as exc:
            raise validation_error(
                "SDS-index kunde inte läsas.", details={"path": str(index_path)}
            ) from exc
