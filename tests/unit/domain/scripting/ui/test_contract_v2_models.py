import pytest
from pydantic import ValidationError

from skriptoteket.domain.scripting.ui.contract_v2 import (
    ToolUiContractV2Result,
    UiBooleanField,
    UiMarkdownOutput,
    UiTableOutput,
)


def test_contract_v2_validates_markdown_output_and_boolean_field() -> None:
    payload = {
        "contract_version": 2,
        "status": "succeeded",
        "error_summary": None,
        "outputs": [{"kind": "markdown", "markdown": "# Hello"}],
        "next_actions": [
            {
                "action_id": "confirm",
                "label": "Confirm",
                "kind": "form",
                "fields": [{"name": "notify", "kind": "boolean", "label": "Notify guardians"}],
                "prefill": {"notify": True},
            }
        ],
        "state": {"flags_confirmed": True},
        "artifacts": [{"path": "output/report.pdf", "bytes": 12}],
    }

    result = ToolUiContractV2Result.model_validate(payload)

    assert isinstance(result.outputs[0], UiMarkdownOutput)
    assert isinstance(result.next_actions[0].fields[0], UiBooleanField)
    assert result.next_actions[0].prefill == {"notify": True}


def test_contract_v2_validates_table_output() -> None:
    payload = {
        "contract_version": 2,
        "status": "succeeded",
        "error_summary": None,
        "outputs": [
            {
                "kind": "table",
                "title": "Students flagged",
                "columns": [{"key": "name", "label": "Name"}, {"key": "reason", "label": "Reason"}],
                "rows": [{"name": "Ada", "reason": "Late 3x"}],
            }
        ],
        "next_actions": [],
        "state": {},
        "artifacts": [],
    }

    result = ToolUiContractV2Result.model_validate(payload)

    assert isinstance(result.outputs[0], UiTableOutput)


def test_contract_v2_rejects_non_object_vega_lite_spec() -> None:
    payload = {
        "contract_version": 2,
        "status": "succeeded",
        "error_summary": None,
        "outputs": [{"kind": "vega_lite", "spec": "not an object"}],
        "next_actions": [],
        "state": {},
        "artifacts": [],
    }

    with pytest.raises(ValidationError):
        ToolUiContractV2Result.model_validate(payload)
