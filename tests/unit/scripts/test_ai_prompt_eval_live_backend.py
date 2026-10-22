"""Live-backend prompt-eval harness tests.

Domain purpose:
    Keep the AI prompt-eval harness aligned with the editor AI routes the
    backend serves today (inline completions and edit-ops), so a healthy
    backend answers every fixture instead of a missing-route error.

Relationships:
    - Drives `scripts.ai_prompt_eval.run_live_backend.run` through a fake HTTP
      transport; no backend, model or credential is contacted.
    - The HuleEdu signing helper is replaced by a stub module because the
      harness only needs the signed header mapping.
"""

from __future__ import annotations

import importlib
import json
import sys
import types
from pathlib import Path

import httpx
import pytest
from pydantic import ValidationError

from scripts.ai_prompt_eval.fixture_bank import FIXTURES, EditSuggestionFixture
from skriptoteket.web.api.v1.editor.models.common import EditorEditOpsPatchOp
from skriptoteket.web.api.v1.editor.models.requests import (
    EditorEditOpsRequest,
    EditorInlineCompletionRequest,
)
from skriptoteket.web.api.v1.editor.models.responses import (
    EditorEditOpsResponse,
    EditorInlineCompletionResponse,
)

COMPLETIONS_PATH = "/api/v1/editor/completions"
EDIT_OPS_PATH = "/api/v1/editor/edit-ops"


class _FakeBackend:
    """Answers only the routes the backend serves; anything else is a 404."""

    def __init__(self) -> None:
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        eval_headers = {"X-Skriptoteket-Eval-Outcome": "ok", "X-Skriptoteket-Eval-Template-Id": "t"}
        if request.url.path == COMPLETIONS_PATH:
            EditorInlineCompletionRequest.model_validate_json(request.content)
            body = EditorInlineCompletionResponse(completion="x = 1", enabled=True)
            return httpx.Response(200, content=body.model_dump_json(), headers=eval_headers)
        if request.url.path == EDIT_OPS_PATH:
            EditorEditOpsRequest.model_validate_json(request.content)
            edit_body = EditorEditOpsResponse(
                enabled=True,
                assistant_message="Klart.",
                ops=[
                    EditorEditOpsPatchOp(
                        op="patch", target_file="tool.py", patch_lines=["@@ -1 +1 @@", "-a", "+b"]
                    )
                ],
                base_fingerprints={"tool.py": "abc"},
            )
            return httpx.Response(200, content=edit_body.model_dump_json(), headers=eval_headers)
        return httpx.Response(404, json={"error": {"code": "not_found"}, "correlation_id": "cid"})


def _run_harness(
    *, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, backend: _FakeBackend
) -> list[dict[str, object]]:
    auth_stub = types.ModuleType("scripts._playwright_huleedu_auth")

    def create_signed_huleedu_api_session(**_: object) -> types.SimpleNamespace:
        return types.SimpleNamespace(signed_headers={"X-Signed": "1"})

    setattr(auth_stub, "create_signed_huleedu_api_session", create_signed_huleedu_api_session)
    monkeypatch.setitem(sys.modules, "scripts._playwright_huleedu_auth", auth_stub)
    monkeypatch.delitem(sys.modules, "scripts.ai_prompt_eval.run_live_backend", raising=False)
    module = importlib.import_module("scripts.ai_prompt_eval.run_live_backend")

    real_client = httpx.Client
    transport = httpx.MockTransport(backend)
    monkeypatch.setattr(
        httpx, "Client", lambda **kwargs: real_client(transport=transport, **kwargs)
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_live_backend",
            "--dotenv",
            str(tmp_path / "missing.env"),
            "--email",
            "eval@example.test",
            "--password",
            "pw",
            "--artifacts-root",
            str(tmp_path / "artifacts"),
            "--base-url",
            "http://eval.test",
        ],
    )

    run_dir = module.run()

    lines = (run_dir / "cases.jsonl").read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines]


def test_every_fixture_reaches_a_served_route(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    backend = _FakeBackend()

    cases = _run_harness(monkeypatch=monkeypatch, tmp_path=tmp_path, backend=backend)

    assert {case["http_status"] for case in cases} == {200}
    assert {case["outcome"] for case in cases} == {"ok"}
    assert {request.url.path for request in backend.requests} == {COMPLETIONS_PATH, EDIT_OPS_PATH}


def test_edit_fixtures_send_the_edit_ops_request_contract(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    backend = _FakeBackend()
    _run_harness(monkeypatch=monkeypatch, tmp_path=tmp_path, backend=backend)

    edit_requests = [
        EditorEditOpsRequest.model_validate_json(request.content)
        for request in backend.requests
        if request.url.path == EDIT_OPS_PATH
    ]
    edit_fixtures = [f for f in FIXTURES if isinstance(f, EditSuggestionFixture)]
    assert len(edit_requests) == len(edit_fixtures) > 0
    for sent, fixture in zip(edit_requests, edit_fixtures, strict=True):
        tool_source = sent.virtual_files.tool_py
        assert sent.active_file == "tool.py"
        assert sent.message == fixture.instruction
        assert sent.selection is not None
        assert tool_source[sent.selection.start : sent.selection.end] == fixture.selection
        assert tool_source == fixture.prefix + fixture.selection + fixture.suffix


def test_timeout_is_recorded_as_a_timeout_outcome(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    class _Slow(_FakeBackend):
        def __call__(self, request: httpx.Request) -> httpx.Response:
            raise httpx.ReadTimeout("slow", request=request)

    cases = _run_harness(monkeypatch=monkeypatch, tmp_path=tmp_path, backend=_Slow())

    assert {case["outcome"] for case in cases} == {"timeout"}
    assert {case["error_kind"] for case in cases} == {"timeout"}


def test_unknown_eval_outcome_header_is_an_error_outcome(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    class _Odd(_FakeBackend):
        def __call__(self, request: httpx.Request) -> httpx.Response:
            response = super().__call__(request)
            response.headers["X-Skriptoteket-Eval-Outcome"] = "surprising"
            return response

    cases = _run_harness(monkeypatch=monkeypatch, tmp_path=tmp_path, backend=_Odd())

    assert {case["outcome"] for case in cases} == {"error"}


def test_edit_fixture_without_instruction_is_rejected() -> None:
    with pytest.raises(ValidationError):
        EditSuggestionFixture.model_validate(
            {"fixture_id": "x", "prefix": "", "selection": "s", "suffix": "", "instruction": None}
        )
