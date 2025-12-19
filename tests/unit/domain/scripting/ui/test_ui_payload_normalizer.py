import json

import pytest

from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.scripting.ui.contract_v2 import (
    ToolUiContractV2Result,
    UiFormAction,
    UiHtmlSandboxedOutput,
    UiMarkdownOutput,
    UiNoticeOutput,
    UiTableOutput,
)
from skriptoteket.domain.scripting.ui.normalizer import DeterministicUiPayloadNormalizer
from skriptoteket.domain.scripting.ui.policy import CURATED_UI_POLICY, DEFAULT_UI_POLICY


def _canonical_json_bytes(value: object) -> bytes:
    dumped = json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=False)
    return dumped.encode("utf-8")


def _utf8_len(value: str) -> int:
    return len(value.encode("utf-8"))


def _actions_from_dicts(actions: list[dict[str, object]]) -> list[UiFormAction]:
    return [UiFormAction.model_validate(action) for action in actions]


def test_normalizer_enforces_markdown_table_html_caps_and_adds_notice() -> None:
    policy = DEFAULT_UI_POLICY

    markdown = "x" * (policy.caps.markdown_max_bytes + 10)
    html = "<div>" + ("x" * (policy.caps.html_sandboxed_max_bytes + 10)) + "</div>"

    columns = [{"key": f"c{i}", "label": f"C{i}"} for i in range(policy.caps.table_max_cols + 1)]
    rows = [{"c0": "x"} for _ in range(policy.caps.table_max_rows + 1)]
    rows[0] = {"c0": "x" * (policy.caps.table_cell_max_bytes + 10)}

    raw = ToolUiContractV2Result.model_validate(
        {
            "contract_version": 2,
            "status": "succeeded",
            "error_summary": None,
            "outputs": [
                {"kind": "markdown", "markdown": markdown},
                {"kind": "html_sandboxed", "html": html},
                {"kind": "table", "title": "T", "columns": columns, "rows": rows},
            ],
            "next_actions": [],
            "state": {},
            "artifacts": [],
        }
    )

    result = DeterministicUiPayloadNormalizer().normalize(
        raw_result=raw,
        backend_actions=[],
        policy=policy,
    )

    markdown_out = next(o for o in result.ui_payload.outputs if isinstance(o, UiMarkdownOutput))
    html_out = next(o for o in result.ui_payload.outputs if isinstance(o, UiHtmlSandboxedOutput))
    table_out = next(o for o in result.ui_payload.outputs if isinstance(o, UiTableOutput))

    assert _utf8_len(markdown_out.markdown) <= policy.caps.markdown_max_bytes
    assert _utf8_len(html_out.html) <= policy.caps.html_sandboxed_max_bytes

    assert len(table_out.columns) <= policy.caps.table_max_cols
    assert len(table_out.rows) <= policy.caps.table_max_rows
    cell = table_out.rows[0]["c0"]
    assert isinstance(cell, str)
    assert _utf8_len(cell) <= policy.caps.table_cell_max_bytes

    assert any(
        isinstance(o, UiNoticeOutput) and o.message.startswith("System notice:")
        for o in result.ui_payload.outputs
    )


def test_normalizer_is_deterministic_across_input_ordering() -> None:
    policy = CURATED_UI_POLICY
    normalizer = DeterministicUiPayloadNormalizer()

    raw1 = ToolUiContractV2Result.model_validate(
        {
            "contract_version": 2,
            "status": "succeeded",
            "error_summary": None,
            "outputs": [
                {
                    "kind": "markdown",
                    "markdown": "x" * (DEFAULT_UI_POLICY.caps.markdown_max_bytes + 5),
                },
                {"kind": "json", "title": "J", "value": {"z": 1, "a": 2}},
            ],
            "next_actions": [
                {
                    "action_id": "tool_b",
                    "label": "B",
                    "kind": "form",
                    "fields": [{"name": "flag", "kind": "boolean", "label": "Flag"}],
                },
                {
                    "action_id": "tool_a",
                    "label": "A",
                    "kind": "form",
                    "fields": [],
                },
            ],
            "state": {"b": 1, "a": 2},
            "artifacts": [],
        }
    )

    raw2 = ToolUiContractV2Result.model_validate(
        {
            "contract_version": 2,
            "status": "succeeded",
            "error_summary": None,
            "outputs": [
                {
                    "kind": "markdown",
                    "markdown": "x" * (DEFAULT_UI_POLICY.caps.markdown_max_bytes + 5),
                },
                {"kind": "json", "title": "J", "value": {"a": 2, "z": 1}},
            ],
            "next_actions": [
                {
                    "action_id": "tool_a",
                    "label": "A",
                    "kind": "form",
                    "fields": [],
                },
                {
                    "action_id": "tool_b",
                    "label": "B",
                    "kind": "form",
                    "fields": [{"name": "flag", "kind": "boolean", "label": "Flag"}],
                },
            ],
            "state": {"a": 2, "b": 1},
            "artifacts": [],
        }
    )

    backend1: list[dict[str, object]] = [
        {
            "action_id": "backend_d",
            "label": "D",
            "kind": "form",
            "fields": [],
        },
        {
            "action_id": "backend_c",
            "label": "C",
            "kind": "form",
            "fields": [],
        },
    ]
    backend_actions1 = _actions_from_dicts(backend1)

    backend2 = list(reversed(backend1))
    backend_actions2 = _actions_from_dicts(backend2)

    result1 = normalizer.normalize(raw_result=raw1, backend_actions=backend_actions1, policy=policy)
    result2 = normalizer.normalize(raw_result=raw2, backend_actions=backend_actions2, policy=policy)

    bytes1 = _canonical_json_bytes(result1.ui_payload.model_dump(mode="json"))
    bytes2 = _canonical_json_bytes(result2.ui_payload.model_dump(mode="json"))

    assert bytes1 == bytes2


def test_normalizer_raises_on_action_id_conflict() -> None:
    raw = ToolUiContractV2Result.model_validate(
        {
            "contract_version": 2,
            "status": "succeeded",
            "error_summary": None,
            "outputs": [],
            "next_actions": [
                {
                    "action_id": "conflict",
                    "label": "A",
                    "kind": "form",
                    "fields": [],
                }
            ],
            "state": {},
            "artifacts": [],
        }
    )

    backend_action = ToolUiContractV2Result.model_validate(
        {
            "contract_version": 2,
            "status": "succeeded",
            "error_summary": None,
            "outputs": [],
            "next_actions": [
                {
                    "action_id": "conflict",
                    "label": "B",
                    "kind": "form",
                    "fields": [],
                }
            ],
            "state": {},
            "artifacts": [],
        }
    ).next_actions[0]

    with pytest.raises(DomainError) as exc_info:
        DeterministicUiPayloadNormalizer().normalize(
            raw_result=raw,
            backend_actions=[backend_action],
            policy=DEFAULT_UI_POLICY,
        )

    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR
