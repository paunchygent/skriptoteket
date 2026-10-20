"""The committed browser format constants match the Python domain truth."""

from __future__ import annotations

from pathlib import Path

from scripts import export_native_exam_document_versions as module
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document_versions import (
    CURRENT_NATIVE_EXAM_DOCUMENT_VERSION,
    NATIVE_EXAM_DOCUMENT_SCHEMA_VERSION,
    OLDEST_READABLE_NATIVE_EXAM_DOCUMENT_VERSION,
)


def test_generated_browser_constants_match_domain_constants() -> None:
    prefix = module.native_exam_document_schema_prefix(
        schema_version=NATIVE_EXAM_DOCUMENT_SCHEMA_VERSION,
        current_version=CURRENT_NATIVE_EXAM_DOCUMENT_VERSION,
    )
    rendered = module.render_native_exam_document_versions(
        prefix=prefix,
        current_version=CURRENT_NATIVE_EXAM_DOCUMENT_VERSION,
        oldest_readable_version=OLDEST_READABLE_NATIVE_EXAM_DOCUMENT_VERSION,
    )
    committed = (
        Path(__file__).resolve().parents[3]
        / "frontend"
        / "apps"
        / "skriptoteket"
        / "src"
        / "api"
        / "nativeExamDocumentVersions.generated.ts"
    )
    assert rendered == committed.read_text(encoding="utf-8")
