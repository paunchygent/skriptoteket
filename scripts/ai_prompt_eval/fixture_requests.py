"""Turn prompt-eval fixtures into the editor AI requests the backend serves."""

from __future__ import annotations

from dataclasses import dataclass
from typing import assert_never
from uuid import UUID

from scripts.ai_prompt_eval.fixture_bank import (
    EditSuggestionFixture,
    InlineCompletionFixture,
    PromptEvalFixture,
)
from skriptoteket.web.api.v1.editor.models.common import (
    EditorEditOpsSelection,
    EditorVirtualFiles,
)
from skriptoteket.web.api.v1.editor.models.requests import (
    EditorEditOpsRequest,
    EditorInlineCompletionRequest,
)

COMPLETIONS_PATH = "/api/v1/editor/completions"
EDIT_OPS_PATH = "/api/v1/editor/edit-ops"

# The edit-ops handler carries the tool id into logs and the door caller only, and the
# harness acts as a superuser, so the evaluation needs no persisted tool.
EVAL_TOOL_ID = UUID("00000000-0000-4000-8000-000000000e7a")


@dataclass(frozen=True)
class FixtureRequest:
    """One POST: the route and the JSON body serialized from the route's request model."""

    path: str
    json_body: str


def _completion_request(fixture: InlineCompletionFixture) -> FixtureRequest:
    request = EditorInlineCompletionRequest(prefix=fixture.prefix, suffix=fixture.suffix)
    return FixtureRequest(path=COMPLETIONS_PATH, json_body=request.model_dump_json())


def _edit_ops_request(fixture: EditSuggestionFixture) -> FixtureRequest:
    selection_start = len(fixture.prefix)
    request = EditorEditOpsRequest(
        tool_id=EVAL_TOOL_ID,
        message=fixture.instruction,
        active_file="tool.py",
        selection=EditorEditOpsSelection(
            start=selection_start, end=selection_start + len(fixture.selection)
        ),
        virtual_files=EditorVirtualFiles(
            tool_py=fixture.prefix + fixture.selection + fixture.suffix,
            entrypoint_txt="",
            settings_schema_json="",
            input_schema_json="",
            usage_instructions_md="",
        ),
    )
    return FixtureRequest(path=EDIT_OPS_PATH, json_body=request.model_dump_json(by_alias=True))


def build_request(fixture: PromptEvalFixture) -> FixtureRequest:
    if isinstance(fixture, InlineCompletionFixture):
        return _completion_request(fixture)
    if isinstance(fixture, EditSuggestionFixture):
        return _edit_ops_request(fixture)
    assert_never(fixture)
