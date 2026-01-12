from __future__ import annotations

import asyncio
import json
import os
import tempfile
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

import structlog

from skriptoteket.config import Settings
from skriptoteket.protocols.llm_captures import LlmCaptureKind, LlmCaptureStoreProtocol

logger = structlog.get_logger(__name__)


def _utc_now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


class ArtifactsLlmCaptureStore(LlmCaptureStoreProtocol):
    """Write sensitive debug captures under ARTIFACTS_ROOT/llm-captures/.

    Captures must never be exposed via tool-developer-facing endpoints. Retrieval is
    filesystem/SSH only.
    """

    def __init__(self, *, settings: Settings) -> None:
        self._root = settings.ARTIFACTS_ROOT / "llm-captures"

    async def write_capture(
        self,
        *,
        kind: LlmCaptureKind,
        capture_id: UUID,
        payload: Mapping[str, object],
    ) -> None:
        try:
            await asyncio.to_thread(
                self._write_sync, kind=kind, capture_id=capture_id, payload=payload
            )
        except Exception as exc:  # noqa: BLE001 - debug capture must never break requests
            logger.warning(
                "llm_capture_write_failed",
                kind=kind,
                capture_id=str(capture_id),
                error_type=type(exc).__name__,
            )

    def _write_sync(
        self, *, kind: LlmCaptureKind, capture_id: UUID, payload: Mapping[str, object]
    ) -> None:
        kind_root = self._root / kind
        kind_root.mkdir(parents=True, exist_ok=True)

        capture_dir = kind_root / str(capture_id)
        capture_dir.mkdir(parents=True, exist_ok=True)
        try:
            os.chmod(capture_dir, 0o700)
        except OSError:
            pass

        envelope = {
            "version": 1,
            "kind": kind,
            "capture_id": str(capture_id),
            "captured_at": _utc_now_iso(),
            "payload": payload,
        }

        final_path = capture_dir / "capture.json"
        if final_path.exists():
            return

        serialized = json.dumps(
            envelope,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            default=str,
        )

        tmp_file = None
        try:
            tmp_file = tempfile.NamedTemporaryFile(
                "w",
                encoding="utf-8",
                dir=capture_dir,
                prefix="capture.",
                suffix=".tmp",
                delete=False,
            )
            tmp_file.write(serialized)
            tmp_file.flush()
            os.fsync(tmp_file.fileno())
            tmp_file.close()

            Path(tmp_file.name).replace(final_path)
        finally:
            if tmp_file is not None and not tmp_file.closed:
                tmp_file.close()
            if tmp_file is not None:
                try:
                    Path(tmp_file.name).unlink(missing_ok=True)
                except OSError:
                    pass

        try:
            os.chmod(final_path, 0o600)
        except OSError:
            pass

        logger.info(
            "llm_capture_written",
            kind=kind,
            capture_id=str(capture_id),
            bytes=len(serialized.encode("utf-8")),
        )
