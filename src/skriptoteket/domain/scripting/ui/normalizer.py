from __future__ import annotations

import json
from dataclasses import dataclass, field

from pydantic import JsonValue

from skriptoteket.domain.errors import validation_error
from skriptoteket.domain.scripting.ui import contract_v2
from skriptoteket.domain.scripting.ui.normalization import UiNormalizationResult
from skriptoteket.domain.scripting.ui.policy import UiPolicy

_SYSTEM_NOTICE_PREFIX = "System notice: "
_TOOL_NOTICE_MAX_BYTES = 8 * 1024


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

    ui_payload_outputs_dropped_due_to_budget: int = 0
    ui_payload_actions_dropped_due_to_budget: int = 0
    ui_payload_budget_notice_added: bool = False


def _canonical_json_bytes(value: object) -> int:
    dumped = json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=False)
    return len(dumped.encode("utf-8"))


def _utf8_truncate(value: str, *, max_bytes: int) -> tuple[str, bool]:
    if max_bytes <= 0:
        return ("", bool(value))
    encoded = value.encode("utf-8")
    if len(encoded) <= max_bytes:
        return (value, False)
    return (encoded[:max_bytes].decode("utf-8", errors="ignore"), True)


def _system_notice(message: str) -> contract_v2.UiNoticeOutput:
    return contract_v2.UiNoticeOutput(
        level=contract_v2.UiNoticeLevel.WARNING,
        message=f"{_SYSTEM_NOTICE_PREFIX}{message}",
    )


def _count_duplicates(values: list[str]) -> set[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return duplicates


def _canonicalize_json_value(
    value: JsonValue,
    *,
    max_depth: int,
    max_keys: int,
    max_array_len: int,
    depth: int = 0,
) -> tuple[JsonValue, bool]:
    if max_depth >= 0 and depth >= max_depth:
        if isinstance(value, dict):
            return ({}, True)
        if isinstance(value, list):
            return ([], True)
        return (value, False)

    if isinstance(value, dict):
        truncated = False
        items: list[tuple[str, JsonValue]] = []
        for key in sorted(value.keys(), key=str):
            if max_keys >= 0 and len(items) >= max_keys:
                truncated = True
                break
            child, child_truncated = _canonicalize_json_value(
                value[key],
                max_depth=max_depth,
                max_keys=max_keys,
                max_array_len=max_array_len,
                depth=depth + 1,
            )
            truncated = truncated or child_truncated
            items.append((str(key), child))
        return ({k: v for k, v in items}, truncated)

    if isinstance(value, list):
        truncated = False
        items: list[JsonValue] = []
        limit = len(value) if max_array_len < 0 else min(len(value), max_array_len)
        if limit < len(value):
            truncated = True
        for item in value[:limit]:
            child, child_truncated = _canonicalize_json_value(
                item,
                max_depth=max_depth,
                max_keys=max_keys,
                max_array_len=max_array_len,
                depth=depth + 1,
            )
            truncated = truncated or child_truncated
            items.append(child)
        return (items, truncated)

    return (value, False)


def _shrink_json_value_to_max_bytes(
    value: JsonValue, *, max_bytes: int
) -> tuple[JsonValue, bool, bool]:
    """Returns (value, was_truncated, fits_budget)."""
    if max_bytes < 2:
        return (value, False, False)

    current = value
    if _canonical_json_bytes(current) <= max_bytes:
        return (current, False, True)

    if isinstance(current, str):
        truncated, did_truncate = _utf8_truncate(current, max_bytes=max_bytes)
        return (truncated, did_truncate, _canonical_json_bytes(truncated) <= max_bytes)

    if isinstance(current, dict):
        items = list(current.items())
        low = 0
        high = len(items)
        best = 0
        while low <= high:
            mid = (low + high) // 2
            candidate = {k: v for k, v in items[:mid]}
            if _canonical_json_bytes(candidate) <= max_bytes:
                best = mid
                low = mid + 1
            else:
                high = mid - 1
        candidate = {k: v for k, v in items[:best]}
        return (candidate, best < len(items), _canonical_json_bytes(candidate) <= max_bytes)

    if isinstance(current, list):
        low = 0
        high = len(current)
        best = 0
        while low <= high:
            mid = (low + high) // 2
            candidate = current[:mid]
            if _canonical_json_bytes(candidate) <= max_bytes:
                best = mid
                low = mid + 1
            else:
                high = mid - 1
        candidate = current[:best]
        return (candidate, best < len(current), _canonical_json_bytes(candidate) <= max_bytes)

    return (current, False, _canonical_json_bytes(current) <= max_bytes)


def _enforce_state_budget(
    state: dict[str, JsonValue],
    *,
    max_bytes: int,
) -> tuple[dict[str, JsonValue], int]:
    if max_bytes < 2:
        return ({}, len(state) if state else 0)

    items = [(key, state[key]) for key in sorted(state.keys())]
    if _canonical_json_bytes({k: v for k, v in items}) <= max_bytes:
        return ({k: v for k, v in items}, 0)

    low = 0
    high = len(items)
    best = 0
    while low <= high:
        mid = (low + high) // 2
        candidate = {k: v for k, v in items[:mid]}
        if _canonical_json_bytes(candidate) <= max_bytes:
            best = mid
            low = mid + 1
        else:
            high = mid - 1

    candidate = {k: v for k, v in items[:best]}
    dropped = len(items) - best
    return (candidate, dropped)


def _normalize_table_output(
    output: contract_v2.UiTableOutput,
    *,
    policy: UiPolicy,
    stats: _NormalizationStats,
) -> contract_v2.UiTableOutput:
    caps = policy.caps

    columns = output.columns[: caps.table_max_cols]
    rows = output.rows[: caps.table_max_rows]

    did_truncate = False
    if len(output.columns) > len(columns) or len(output.rows) > len(rows):
        did_truncate = True

    col_keys = [col.key for col in columns]
    normalized_rows: list[contract_v2.UiTableRow] = []
    for row in rows:
        normalized_row: contract_v2.UiTableRow = {}
        for key in col_keys:
            if key not in row:
                continue
            cell = row[key]
            if isinstance(cell, str):
                truncated, did_truncate_cell = _utf8_truncate(
                    cell,
                    max_bytes=caps.table_cell_max_bytes,
                )
                if did_truncate_cell:
                    did_truncate = True
                normalized_row[key] = truncated
            else:
                normalized_row[key] = cell
        normalized_rows.append(normalized_row)

    if did_truncate:
        stats.tables_truncated += 1

    return output.model_copy(update={"columns": columns, "rows": normalized_rows})


def _normalize_json_output(
    output: contract_v2.UiJsonOutput,
    *,
    policy: UiPolicy,
    stats: _NormalizationStats,
) -> contract_v2.UiJsonOutput | None:
    caps = policy.caps

    canonical, truncated_tree = _canonicalize_json_value(
        output.value,
        max_depth=caps.json_max_depth,
        max_keys=caps.json_max_keys,
        max_array_len=caps.json_max_array_len,
    )
    shrunk, truncated_bytes, fits = _shrink_json_value_to_max_bytes(
        canonical, max_bytes=caps.json_max_bytes
    )
    if not fits:
        return None

    if truncated_tree or truncated_bytes:
        stats.json_truncated += 1
    return output.model_copy(update={"value": shrunk})


def _normalize_outputs(
    raw_outputs: list[contract_v2.UiOutput],
    *,
    policy: UiPolicy,
    stats: _NormalizationStats,
) -> list[contract_v2.UiOutput]:
    caps = policy.caps

    normalized: list[contract_v2.UiOutput] = []
    to_process = raw_outputs[: caps.max_outputs]
    stats.outputs_dropped_due_to_max_outputs += max(0, len(raw_outputs) - len(to_process))

    for output in to_process:
        if output.kind not in policy.allowed_output_kinds:
            stats.outputs_dropped_disallowed[output.kind] = (
                stats.outputs_dropped_disallowed.get(output.kind, 0) + 1
            )
            continue

        if isinstance(output, contract_v2.UiNoticeOutput):
            truncated, did_truncate = _utf8_truncate(
                output.message,
                max_bytes=_TOOL_NOTICE_MAX_BYTES,
            )
            if did_truncate:
                stats.notices_truncated += 1
                output = output.model_copy(update={"message": truncated})
            normalized.append(output)
            continue

        if isinstance(output, contract_v2.UiMarkdownOutput):
            truncated, did_truncate = _utf8_truncate(
                output.markdown,
                max_bytes=caps.markdown_max_bytes,
            )
            if did_truncate:
                stats.markdown_truncated += 1
                output = output.model_copy(update={"markdown": truncated})
            normalized.append(output)
            continue

        if isinstance(output, contract_v2.UiHtmlSandboxedOutput):
            truncated, did_truncate = _utf8_truncate(
                output.html,
                max_bytes=caps.html_sandboxed_max_bytes,
            )
            if did_truncate:
                stats.html_truncated += 1
                output = output.model_copy(update={"html": truncated})
            normalized.append(output)
            continue

        if isinstance(output, contract_v2.UiTableOutput):
            normalized.append(_normalize_table_output(output, policy=policy, stats=stats))
            continue

        if isinstance(output, contract_v2.UiJsonOutput):
            normalized_json = _normalize_json_output(output, policy=policy, stats=stats)
            if normalized_json is None:
                stats.json_dropped += 1
                continue
            normalized.append(normalized_json)
            continue

        if isinstance(output, contract_v2.UiVegaLiteOutput):
            stats.vega_lite_blocked += 1
            continue

        normalized.append(output)

    return normalized


def _normalize_actions(
    raw_actions: list[contract_v2.UiFormAction],
    backend_actions: list[contract_v2.UiFormAction],
    *,
    policy: UiPolicy,
    stats: _NormalizationStats,
) -> list[contract_v2.UiFormAction]:
    raw_ids = [action.action_id for action in raw_actions]
    backend_ids = [action.action_id for action in backend_actions]

    raw_duplicates = _count_duplicates(raw_ids)
    if raw_duplicates:
        raise validation_error(
            "Duplicate action_id in tool-provided next_actions",
            details={"duplicates": sorted(raw_duplicates)},
        )

    backend_duplicates = _count_duplicates(backend_ids)
    if backend_duplicates:
        raise validation_error(
            "Duplicate action_id in backend-injected actions",
            details={"duplicates": sorted(backend_duplicates)},
        )

    conflicts = set(raw_ids) & set(backend_ids)
    if conflicts:
        raise validation_error(
            "Action IDs must be unique across tool and backend actions",
            details={"conflicts": sorted(conflicts)},
        )

    combined = sorted(raw_actions, key=lambda action: action.action_id) + sorted(
        backend_actions, key=lambda action: action.action_id
    )

    normalized: list[contract_v2.UiFormAction] = []
    for action in combined:
        fields: list[contract_v2.UiActionField] = []
        for field_item in action.fields:
            if field_item.kind not in policy.allowed_action_field_kinds:
                stats.fields_dropped_disallowed[field_item.kind] = (
                    stats.fields_dropped_disallowed.get(field_item.kind, 0) + 1
                )
                continue

            if isinstance(field_item, contract_v2.UiEnumField):
                if len(field_item.options) > policy.caps.enum_max_options:
                    stats.enum_options_truncated += 1
                    field_item = field_item.model_copy(
                        update={"options": field_item.options[: policy.caps.enum_max_options]}
                    )

            if isinstance(field_item, contract_v2.UiMultiEnumField):
                if len(field_item.options) > policy.caps.multi_enum_max_options:
                    stats.multi_enum_options_truncated += 1
                    field_item = field_item.model_copy(
                        update={"options": field_item.options[: policy.caps.multi_enum_max_options]}
                    )

            fields.append(field_item)

        if len(fields) > policy.caps.max_fields_per_action:
            stats.fields_dropped_due_to_max_fields += (
                len(fields) - policy.caps.max_fields_per_action
            )
            fields = fields[: policy.caps.max_fields_per_action]

        normalized.append(action.model_copy(update={"fields": fields}))

    if len(normalized) > policy.caps.max_next_actions:
        stats.actions_dropped_due_to_max_next_actions += (
            len(normalized) - policy.caps.max_next_actions
        )
        normalized = normalized[: policy.caps.max_next_actions]

    return normalized


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

    for kind in sorted(stats.outputs_dropped_disallowed.keys(), key=lambda k: k.value):
        count = stats.outputs_dropped_disallowed[kind]
        notices.append(
            _system_notice(f"Dropped {count} '{kind.value}' outputs (not allowed by policy).")
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
    for kind in sorted(stats.fields_dropped_disallowed.keys(), key=lambda k: k.value):
        count = stats.fields_dropped_disallowed[kind]
        notices.append(
            _system_notice(
                f"Dropped {count} action fields of kind '{kind.value}' (not allowed by policy)."
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


class DeterministicUiPayloadNormalizer:
    def normalize(
        self,
        *,
        raw_result: contract_v2.ToolUiContractV2Result,
        backend_actions: list[contract_v2.UiFormAction],
        policy: UiPolicy,
    ) -> UiNormalizationResult:
        stats = _NormalizationStats()

        raw_state = raw_result.state or {}
        state_canonical: dict[str, JsonValue] = {}
        for key in sorted(raw_state.keys()):
            canonical, truncated = _canonicalize_json_value(
                raw_state[key],
                max_depth=policy.caps.json_max_depth,
                max_keys=policy.caps.json_max_keys,
                max_array_len=policy.caps.json_max_array_len,
            )
            state_canonical[key] = canonical
            stats.state_truncated_to_json_caps = stats.state_truncated_to_json_caps or truncated

        state_normalized, state_keys_dropped = _enforce_state_budget(
            state_canonical,
            max_bytes=policy.budgets.state_max_bytes,
        )
        stats.state_keys_dropped = state_keys_dropped

        tool_outputs = _normalize_outputs(raw_result.outputs, policy=policy, stats=stats)
        actions = _normalize_actions(
            raw_result.next_actions,
            backend_actions,
            policy=policy,
            stats=stats,
        )

        system_notices: list[contract_v2.UiNoticeOutput] = []

        for _ in range(5):
            system_notices = _build_system_notices(policy=policy, stats=stats)

            max_outputs = policy.caps.max_outputs
            if max_outputs >= 0:
                reserved = len(system_notices)
                if reserved >= max_outputs:
                    stats.outputs_dropped_due_to_max_outputs += len(tool_outputs)
                    tool_outputs = []
                    system_notices = system_notices[:max_outputs]
                else:
                    allowed_tool_outputs = max_outputs - reserved
                    if len(tool_outputs) > allowed_tool_outputs:
                        stats.outputs_dropped_due_to_max_outputs += (
                            len(tool_outputs) - allowed_tool_outputs
                        )
                        tool_outputs = tool_outputs[:allowed_tool_outputs]

            tool_outputs, system_notices, actions = _enforce_ui_payload_budgets(
                tool_outputs,
                system_notices,
                actions,
                policy=policy,
                stats=stats,
            )

            needs_output_cap_notice = stats.outputs_dropped_due_to_max_outputs > 0
            has_output_cap_notice = any(
                notice.message.startswith(f"{_SYSTEM_NOTICE_PREFIX}Output list capped")
                for notice in system_notices
            )
            needs_budget_notice = stats.ui_payload_budget_notice_added
            has_budget_notice = any(
                notice.message.startswith(f"{_SYSTEM_NOTICE_PREFIX}ui_payload exceeded")
                for notice in system_notices
            )
            if (not needs_output_cap_notice or has_output_cap_notice) and (
                not needs_budget_notice or has_budget_notice
            ):
                break

        ui_payload = contract_v2.UiPayloadV2(
            outputs=[*tool_outputs, *system_notices],
            next_actions=actions,
        )
        return UiNormalizationResult(ui_payload=ui_payload, state=state_normalized)
