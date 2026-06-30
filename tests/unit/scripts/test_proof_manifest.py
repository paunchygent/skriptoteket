"""Proof manifest persistence tests.

Domain purpose:
    Lock the retained Playwright proof manifest policy so developer fixtures
    and uploaded exam evidence are preserved as ordinary proof data.

Relationships:
    Exercises `scripts._proof_manifest`, which is shared by authenticated
    browser proof scripts that write `.artifacts/` evidence.
"""

from __future__ import annotations

import json
from pathlib import Path

from scripts._proof_manifest import (
    LEGACY_MANIFEST_NAME,
    PRIMARY_MANIFEST_NAME,
    write_proof_manifest,
)


def test_write_proof_manifest_keeps_fixture_content_and_legacy_alias(tmp_path: Path) -> None:
    summary = {
        "uploaded_source_dxe": "/fixtures/ak7_lag_och_ratt_with_image.dxe",
        "exam_fixture_text": "Public developer fixture exam content",
        "download_status": 200,
    }

    primary_path = write_proof_manifest(tmp_path, summary)

    assert primary_path == tmp_path / PRIMARY_MANIFEST_NAME
    assert json.loads(primary_path.read_text(encoding="utf-8")) == summary
    assert json.loads((tmp_path / LEGACY_MANIFEST_NAME).read_text(encoding="utf-8")) == summary
