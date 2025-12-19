from __future__ import annotations

from skriptoteket.domain.scripting.ui import contract_v2
from skriptoteket.domain.scripting.ui.policy import UiPolicy

from ._json_canonical import _canonical_json_bytes
from ._stats import _NormalizationStats

_SYSTEM_NOTICE_PREFIX = "System notice: "


def _system_notice(message: str) -> contract_v2.UiNoticeOutput:
    return contract_v2.UiNoticeOutput(
        level=contract_v2.UiNoticeLevel.WARNING,
        message=f"{_SYSTEM_NOTICE_PREFIX}{message}",
    )


def _build_system_notices(
    *,
    policy: UiPolicy,
    stats: _NormalizationStats,
) -> list[contract_v2.UiNoticeOutput]:
    notices: list[contract_v2.UiNoticeOutput] = []

    if stats.state_truncated_to_json_caps:
        notices.append(_system_notice("State values were truncated to platform JSON caps."))

    if stats.state_keys_dropped:
        notices.append(
            _system_notice(
                f"State truncated to fit {policy.budgets.state_max_bytes} bytes "
                f"(dropped {stats.state_keys_dropped} keys)."
            )
        )

    if stats.vega_lite_blocked:
        notices.append(
            _system_notice(
                "vega_lite output is currently blocked until platform restrictions are implemented."
            )
        )

    for output_kind in sorted(stats.outputs_dropped_disallowed.keys(), key=lambda k: k.value):
        count = stats.outputs_dropped_disallowed[output_kind]
        notices.append(
            _system_notice(
                f"Dropped {count} '{output_kind.value}' outputs (not allowed by policy)."
            )
        )

    if stats.outputs_dropped_due_to_max_outputs:
        notices.append(
            _system_notice(
                f"Output list capped at {policy.caps.max_outputs} "
                f"(dropped {stats.outputs_dropped_due_to_max_outputs})."
            )
        )

    if stats.notices_truncated:
        notices.append(_system_notice("Truncated tool-provided notice messages."))
    if stats.markdown_truncated:
        notices.append(
            _system_notice(
                f"Truncated {stats.markdown_truncated} markdown outputs to "
                f"{policy.caps.markdown_max_bytes} bytes."
            )
        )
    if stats.html_truncated:
        notices.append(
            _system_notice(
                f"Truncated {stats.html_truncated} html_sandboxed outputs to "
                f"{policy.caps.html_sandboxed_max_bytes} bytes."
            )
        )
    if stats.tables_truncated:
        notices.append(
            _system_notice(
                f"Truncated {stats.tables_truncated} table outputs to platform "
                "row/column/cell caps."
            )
        )
    if stats.json_truncated:
        notices.append(
            _system_notice(f"Truncated {stats.json_truncated} json outputs to platform caps.")
        )
    if stats.json_dropped:
        notices.append(
            _system_notice(
                f"Dropped {stats.json_dropped} json outputs that could not fit within caps."
            )
        )

    if stats.actions_dropped_due_to_max_next_actions:
        notices.append(
            _system_notice(
                f"Next actions capped at {policy.caps.max_next_actions} "
                f"(dropped {stats.actions_dropped_due_to_max_next_actions})."
            )
        )
    for field_kind in sorted(stats.fields_dropped_disallowed.keys(), key=lambda k: k.value):
        count = stats.fields_dropped_disallowed[field_kind]
        notices.append(
            _system_notice(
                f"Dropped {count} action fields of kind '{field_kind.value}' "
                "(not allowed by policy)."
            )
        )
    if stats.fields_dropped_due_to_max_fields:
        notices.append(
            _system_notice(
                f"Action fields capped at {policy.caps.max_fields_per_action}/action "
                f"(dropped {stats.fields_dropped_due_to_max_fields})."
            )
        )
    if stats.enum_options_truncated:
        notices.append(
            _system_notice(
                f"Truncated {stats.enum_options_truncated} enum fields to "
                f"{policy.caps.enum_max_options} options."
            )
        )
    if stats.multi_enum_options_truncated:
        notices.append(
            _system_notice(
                f"Truncated {stats.multi_enum_options_truncated} multi_enum fields to "
                f"{policy.caps.multi_enum_max_options} options."
            )
        )

    if stats.ui_payload_budget_notice_added:
        notices.append(
            _system_notice(
                f"ui_payload exceeded {policy.budgets.ui_payload_max_bytes} bytes "
                f"and was truncated."
            )
        )

    return notices


def _enforce_ui_payload_budgets(
    tool_outputs: list[contract_v2.UiOutput],
    system_notices: list[contract_v2.UiNoticeOutput],
    actions: list[contract_v2.UiFormAction],
    *,
    policy: UiPolicy,
    stats: _NormalizationStats,
) -> tuple[
    list[contract_v2.UiOutput],
    list[contract_v2.UiNoticeOutput],
    list[contract_v2.UiFormAction],
]:
    def current_size() -> int:
        ui_payload = contract_v2.UiPayloadV2(
            outputs=[*tool_outputs, *system_notices],
            next_actions=actions,
        )
        return _canonical_json_bytes(ui_payload.model_dump(mode="json"))

    max_bytes = policy.budgets.ui_payload_max_bytes
    if max_bytes < 2:
        return ([], [], [])

    if current_size() <= max_bytes:
        return (tool_outputs, system_notices, actions)

    did_truncate = False
    while tool_outputs and current_size() > max_bytes:
        tool_outputs.pop()
        stats.ui_payload_outputs_dropped_due_to_budget += 1
        did_truncate = True

    while actions and current_size() > max_bytes:
        actions.pop()
        stats.ui_payload_actions_dropped_due_to_budget += 1
        did_truncate = True

    while system_notices and current_size() > max_bytes:
        system_notices.pop()
        did_truncate = True

    if did_truncate:
        stats.ui_payload_budget_notice_added = True

    return (tool_outputs, system_notices, actions)
