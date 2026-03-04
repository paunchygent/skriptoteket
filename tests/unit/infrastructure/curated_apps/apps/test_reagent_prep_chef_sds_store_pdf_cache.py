from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from skriptoteket.infrastructure.curated_apps.apps.reagent_prep_chef.sds_store import (
    FileSystemReagentPrepChefSdsStore,
)


class _StubPdfRenderer:
    def __init__(self) -> None:
        self.calls: int = 0

    def render_html(self, *, html: str) -> bytes:
        assert "<!doctype html>" in html
        self.calls += 1
        return b"%PDF-1.4\n%stub\n"


def _write_index(*, path: Path, md_file_name: str) -> None:
    payload = {
        "version": 1,
        "as_of": "2026-03-04",
        "entries": {
            "NaCl": {
                "key": "NaCl",
                "display_name": "Natriumklorid",
                "sds_ref": "NaCl",
                "md_file_name": md_file_name,
                "provider": "carlroth",
                "revision": "undated",
                "pdf_file_name": None,
            }
        },
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_get_pdf_generates_and_uses_cache(tmp_path: Path) -> None:
    index_path = tmp_path / "index.json"
    markdown_dir = tmp_path / "markdown"
    cache_dir = tmp_path / "cache"
    markdown_dir.mkdir(parents=True, exist_ok=True)

    md_file_name = "NaCl__carlroth__undated.md"
    _write_index(path=index_path, md_file_name=md_file_name)

    md_path = markdown_dir / md_file_name
    md_path.write_text("# Säkerhetsdatablad\n\n## AVSNITT 1\n\n| A | B |\n| - | - |\n| 1 | 2 |\n")

    renderer = _StubPdfRenderer()
    store = FileSystemReagentPrepChefSdsStore(
        index_path=index_path,
        markdown_dir=markdown_dir,
        pdf_cache_dir=cache_dir,
        pdf_renderer=renderer,
    )

    filename_1, pdf_1, media_type_1 = store.get_pdf(sds_ref="NaCl")
    assert media_type_1 == "application/pdf"
    assert filename_1.endswith(".pdf")
    assert pdf_1.startswith(b"%PDF")
    assert renderer.calls == 1

    cached_path = cache_dir / filename_1
    assert cached_path.is_file()

    filename_2, pdf_2, media_type_2 = store.get_pdf(sds_ref="NaCl")
    assert (filename_2, media_type_2) == (filename_1, media_type_1)
    assert pdf_2 == pdf_1
    assert renderer.calls == 1

    pdf_mtime = cached_path.stat().st_mtime
    os.utime(md_path, (pdf_mtime + 10, pdf_mtime + 10))

    filename_3, pdf_3, media_type_3 = store.get_pdf(sds_ref="NaCl")
    assert (filename_3, media_type_3) == (filename_1, media_type_1)
    assert pdf_3.startswith(b"%PDF")
    assert renderer.calls == 2


def test_get_pdf_returns_content_even_if_cache_unwritable(tmp_path: Path) -> None:
    if os.name == "nt":
        pytest.skip("chmod-based permission test is not reliable on Windows.")

    index_path = tmp_path / "index.json"
    markdown_dir = tmp_path / "markdown"
    cache_dir = tmp_path / "cache"
    markdown_dir.mkdir(parents=True, exist_ok=True)
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_dir.chmod(0o555)

    md_file_name = "NaCl__carlroth__undated.md"
    _write_index(path=index_path, md_file_name=md_file_name)
    (markdown_dir / md_file_name).write_text("# SDS\n")

    store = FileSystemReagentPrepChefSdsStore(
        index_path=index_path,
        markdown_dir=markdown_dir,
        pdf_cache_dir=cache_dir,
        pdf_renderer=_StubPdfRenderer(),
    )

    filename, pdf_bytes, media_type = store.get_pdf(sds_ref="NaCl")
    assert media_type == "application/pdf"
    assert filename.endswith(".pdf")
    assert pdf_bytes.startswith(b"%PDF")
    assert not (cache_dir / filename).is_file()
