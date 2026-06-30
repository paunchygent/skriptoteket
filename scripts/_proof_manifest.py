"""Browser-proof manifest retention policy.

Domain purpose:
    Persist live proof manifests while treating developer fixtures, uploaded
    exam data, and derived artifact evidence as proof data rather than private
    data by default.

Relationships:
    Shared by authenticated Playwright proof scripts that retain Dev/Prod
    evidence under `.artifacts/` and still need the legacy manifest filename for
    older docs and tooling.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

PRIMARY_MANIFEST_NAME = "manifest.json"
LEGACY_MANIFEST_NAME = "manifest.redacted.json"


def write_proof_manifest(artifact_dir: Path, summary: Mapping[str, Any]) -> Path:
    """Write the primary proof manifest and the legacy compatibility alias."""
    encoded = json.dumps(summary, ensure_ascii=False, indent=2)
    primary_path = artifact_dir / PRIMARY_MANIFEST_NAME
    primary_path.write_text(encoded, encoding="utf-8")
    (artifact_dir / LEGACY_MANIFEST_NAME).write_text(encoded, encoding="utf-8")
    return primary_path
