"""Unit tests for the edit-ops harness: recorded responses are the full HTTP responses."""

from __future__ import annotations

import importlib.util
import json
import sys
import types
from pathlib import Path

from pydantic import JsonValue

if importlib.util.find_spec("scripts._playwright_huleedu_auth") is None:
    # The harness imports a signed-session helper that this checkout does not contain;
    # the tests never open a session, so a placeholder module satisfies the import.
    _auth_stub = types.ModuleType("scripts._playwright_huleedu_auth")
    setattr(_auth_stub, "create_signed_huleedu_api_session", lambda **_: None)
    sys.modules["scripts._playwright_huleedu_auth"] = _auth_stub

from scripts.edit_ops_harness import HarnessClient, _run_preview_apply  # noqa: E402
from skriptoteket.web.api.v1.editor.models.common import EditorVirtualFiles  # noqa: E402
from skriptoteket.web.api.v1.editor.models.responses import (  # noqa: E402
    EditorEditOpsPreviewErrorDetails,
    EditorEditOpsPreviewMeta,
    EditorEditOpsPreviewResponse,
)


class _ScriptedClient(HarnessClient):
    """Answer harness requests with queued response bodies and record the request payloads."""

    def __init__(self, bodies: list[dict[str, JsonValue]]) -> None:
        self._bodies = bodies
        self.sent: list[tuple[str, dict[str, JsonValue] | None]] = []

    def close(self) -> None:
        return None

    def request(
        self,
        method: str,
        path: str,
        *,
        payload: dict[str, JsonValue] | None,
        correlation_id: str,
    ) -> dict[str, JsonValue]:
        self.sent.append((path, payload))
        return self._bodies.pop(0)


def _preview_body(*, ok: bool) -> dict[str, JsonValue]:
    response = EditorEditOpsPreviewResponse(
        ok=ok,
        after_virtual_files=EditorVirtualFiles(
            tool_py="print('after')\n",
            entrypoint_txt="run\n",
            settings_schema_json="",
            input_schema_json="",
            usage_instructions_md="",
        ),
        errors=[] if ok else ["Hunk did not apply"],
        error_details=[]
        if ok
        else [
            EditorEditOpsPreviewErrorDetails(op_index=0, hunk_index=1, hunk_header="@@ -1 +1 @@")
        ],
        meta=EditorEditOpsPreviewMeta(
            base_hash="hash-1",
            patch_id="patch-1",
            requires_confirmation=False,
            fuzz_level_used=2,
            max_offset=3,
            normalizations_applied=["trailing_whitespace"],
            applied_cleanly=ok,
        ),
    )
    body: JsonValue = json.loads(response.model_dump_json())
    assert isinstance(body, dict)
    return body


def _read(path: Path) -> JsonValue:
    data: JsonValue = json.loads(path.read_text(encoding="utf-8"))
    return data


def test_preview_and_apply_record_the_full_http_responses(tmp_path: Path) -> None:
    preview_body = _preview_body(ok=True)
    apply_body = _preview_body(ok=True)
    client = _ScriptedClient([preview_body, apply_body])
    preview_request: dict[str, JsonValue] = {"tool_id": "tool-1", "ops": [{"op": "patch"}]}

    ok = _run_preview_apply(
        client,
        preview_request=preview_request,
        mode="full",
        correlation_id="corr",
        output_record_dir=tmp_path,
    )

    assert ok is True
    assert _read(tmp_path / "preview.response.json") == preview_body
    assert _read(tmp_path / "apply.response.json") == apply_body
    recorded_preview = _read(tmp_path / "preview.response.json")
    assert isinstance(recorded_preview, dict)
    assert set(recorded_preview) == {"ok", "after_virtual_files", "errors", "error_details", "meta"}
    apply_path, apply_request = client.sent[1]
    assert apply_path == "/api/v1/editor/edit-ops/apply"
    assert apply_request == {**preview_request, "base_hash": "hash-1", "patch_id": "patch-1"}


def test_failed_preview_records_errors_and_skips_apply(tmp_path: Path) -> None:
    preview_body = _preview_body(ok=False)
    client = _ScriptedClient([preview_body])

    ok = _run_preview_apply(
        client,
        preview_request={"tool_id": "tool-1"},
        mode="full",
        correlation_id="corr",
        output_record_dir=tmp_path,
    )

    assert ok is False
    assert len(client.sent) == 1
    recorded = _read(tmp_path / "preview.response.json")
    assert recorded == preview_body
    assert isinstance(recorded, dict)
    assert recorded["errors"] == ["Hunk did not apply"]
    assert not (tmp_path / "apply.response.json").exists()
