from __future__ import annotations

from skriptoteket.domain.scripting.ui import contract_v2
from skriptoteket.domain.scripting.ui.policy import UiPolicy

from ._json_canonical import (
    _canonicalize_json_value,
    _shrink_json_value_to_max_bytes,
    _utf8_truncate,
)
from ._stats import _NormalizationStats

_TOOL_NOTICE_MAX_BYTES = 8 * 1024


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

