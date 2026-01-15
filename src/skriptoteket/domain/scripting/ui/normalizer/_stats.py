from __future__ import annotations

from dataclasses import dataclass, field

from skriptoteket.domain.scripting.ui import contract_v2


@dataclass(slots=True)
class _NormalizationStats:
    state_keys_dropped: int = 0
    state_truncated_to_json_caps: bool = False

    outputs_dropped_due_to_max_outputs: int = 0
    outputs_dropped_disallowed: dict[contract_v2.UiOutputKind, int] = field(default_factory=dict)
    vega_lite_blocked: int = 0

    notices_truncated: int = 0
    markdown_truncated: int = 0
    html_truncated: int = 0
    tables_truncated: int = 0
    json_truncated: int = 0
    json_dropped: int = 0

    actions_dropped_due_to_max_next_actions: int = 0
    fields_dropped_due_to_max_fields: int = 0
    fields_dropped_disallowed: dict[contract_v2.UiActionFieldKind, int] = field(
        default_factory=dict
    )
    enum_options_truncated: int = 0
    multi_enum_options_truncated: int = 0
    action_prefill_dropped: list[tuple[str, str, str]] = field(default_factory=list)

    ui_payload_outputs_dropped_due_to_budget: int = 0
    ui_payload_actions_dropped_due_to_budget: int = 0
    ui_payload_budget_notice_added: bool = False
