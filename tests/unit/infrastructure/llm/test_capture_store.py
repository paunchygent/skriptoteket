from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

import pytest

from skriptoteket.config import Settings
from skriptoteket.infrastructure.llm.capture_store import ArtifactsLlmCaptureStore


@pytest.mark.unit
@pytest.mark.asyncio
async def test_capture_store_writes_envelope(tmp_path: Path) -> None:
    settings = Settings(ARTIFACTS_ROOT=tmp_path)
    store = ArtifactsLlmCaptureStore(settings=settings)
    capture_id = uuid4()

    await store.write_capture(
        kind="chat_ops_response",
        capture_id=capture_id,
        payload={"hello": "world"},
    )

    capture_path = (
        tmp_path / "llm-captures" / "chat_ops_response" / str(capture_id) / "capture.json"
    )
    assert capture_path.exists()

    payload = json.loads(capture_path.read_text(encoding="utf-8"))
    assert payload["version"] == 1
    assert payload["kind"] == "chat_ops_response"
    assert payload["capture_id"] == str(capture_id)
    assert "captured_at" in payload
    assert payload["payload"]["hello"] == "world"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_capture_store_does_not_raise_when_root_is_not_a_directory(tmp_path: Path) -> None:
    artifacts_root = tmp_path / "artifacts-file"
    artifacts_root.write_text("not a directory", encoding="utf-8")
    store = ArtifactsLlmCaptureStore(settings=Settings(ARTIFACTS_ROOT=artifacts_root))

    await store.write_capture(
        kind="chat_ops_response",
        capture_id=uuid4(),
        payload={"hello": "world"},
    )
