from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest
from structlog.contextvars import bind_contextvars, clear_contextvars

from skriptoteket.application.editor.edit_ops_preview_handler import EditOpsPreviewHandler
from skriptoteket.config import Settings
from skriptoteket.domain.identity.models import Role
from skriptoteket.protocols.llm import EditOpsPatchOp, EditOpsPreviewCommand
from skriptoteket.protocols.llm_captures import LlmCaptureStoreProtocol
from tests.fixtures.identity_fixtures import make_user


@contextmanager
def _bound_correlation_id(correlation_id: UUID):
    clear_contextvars()
    bind_contextvars(correlation_id=str(correlation_id))
    try:
        yield
    finally:
        clear_contextvars()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_preview_writes_capture_on_coherency_error_when_enabled() -> None:
    correlation_id = uuid4()
    with _bound_correlation_id(correlation_id):
        settings = Settings(LLM_CAPTURE_ON_ERROR_ENABLED=True)
        capture_store = MagicMock(spec=LlmCaptureStoreProtocol)
        capture_store.write_capture = AsyncMock()

        handler = EditOpsPreviewHandler(
            settings=settings,
            capture_store=capture_store,
            patch_applier=MagicMock(),
        )
        actor = make_user(role=Role.CONTRIBUTOR)
        tool_id = uuid4()

        patch_lines = [
            "diff --git a/tool.py b/tool.py",
            "--- a/tool.py",
            "+++ b/tool.py",
            "@@ -1 +1 @@",
            "-print('hi')",
            "+print('hej')",
        ]
        result = await handler.handle(
            actor=actor,
            command=EditOpsPreviewCommand(
                tool_id=tool_id,
                active_file="tool.py",
                selection=None,
                cursor=None,
                virtual_files={"tool.py": "print('hi')\n"},
                ops=[
                    EditOpsPatchOp(op="patch", target_file="tool.py", patch_lines=patch_lines),
                    EditOpsPatchOp(op="patch", target_file="tool.py", patch_lines=patch_lines),
                ],
            ),
        )

        assert result.ok is False

        capture_store.write_capture.assert_awaited_once()
        kwargs = capture_store.write_capture.await_args.kwargs
        assert kwargs["kind"] == "edit_ops_preview_failure"
        assert kwargs["capture_id"] == correlation_id
        payload = kwargs["payload"]
        assert payload["outcome"] == "coherency_error"
        assert payload["error_kind"] == "coherency_error"
        assert payload["op_count"] == 2
