from __future__ import annotations

import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID


def prune_artifacts_root(
    *, artifacts_root: Path, retention_days: int, now: datetime | None = None
) -> int:
    if retention_days < 0:
        raise ValueError("retention_days must be >= 0")

    if now is None:
        now = datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")

    if not artifacts_root.exists():
        return 0

    cutoff = now - timedelta(days=retention_days)
    deleted = 0

    for entry in artifacts_root.iterdir():
        if not entry.is_dir():
            continue
        try:
            UUID(entry.name)
        except ValueError:
            continue

        mtime = datetime.fromtimestamp(entry.stat().st_mtime, tz=timezone.utc)
        if mtime >= cutoff:
            continue

        shutil.rmtree(entry)
        deleted += 1

    return deleted


def prune_llm_captures_root(
    *, artifacts_root: Path, retention_days: int, now: datetime | None = None
) -> int:
    """Prune platform-only LLM captures under ARTIFACTS_ROOT/llm-captures/.

    Capture directories are expected at:
      ARTIFACTS_ROOT/llm-captures/<kind>/<capture_id>/

    Where <capture_id> is a UUID (we use the request correlation id).
    """
    if retention_days < 0:
        raise ValueError("retention_days must be >= 0")

    if now is None:
        now = datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")

    captures_root = artifacts_root / "llm-captures"
    if not captures_root.exists():
        return 0

    cutoff = now - timedelta(days=retention_days)
    deleted = 0

    for kind_dir in captures_root.iterdir():
        if not kind_dir.is_dir():
            continue

        for entry in kind_dir.iterdir():
            if not entry.is_dir():
                continue
            try:
                UUID(entry.name)
            except ValueError:
                continue

            mtime = datetime.fromtimestamp(entry.stat().st_mtime, tz=timezone.utc)
            if mtime >= cutoff:
                continue

            shutil.rmtree(entry)
            deleted += 1

    return deleted
