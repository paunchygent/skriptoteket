from __future__ import annotations

from skriptoteket.config import Settings
from skriptoteket.domain.scripting.ui.policy import DEFAULT_UI_POLICY, UiPolicy


def _format_bytes(bytes_count: int) -> str:
    if bytes_count % 1024 == 0:
        return f"{bytes_count} bytes ({bytes_count // 1024} KiB)"
    return f"{bytes_count} bytes"


def contract_v2_fragment(*, policy: UiPolicy = DEFAULT_UI_POLICY) -> str:
    allowed_output_kinds = ", ".join(sorted(kind.value for kind in policy.allowed_output_kinds))
    allowed_action_field_kinds = ", ".join(
        sorted(kind.value for kind in policy.allowed_action_field_kinds)
    )

    caps = policy.caps
    budgets = policy.budgets

    return "\n".join(
        [
            "## Skriptoteket UI payload (outputs/next_actions/state)",
            "",
            "Tool scripts return a dict with:",
            "- `outputs`: list[UiOutput] (can be empty)",
            "- `next_actions`: list[UiFormAction] (can be empty)",
            "- `state`: dict[str, JSON] or None",
            "",
            f"Allowed output kinds (active policy): {allowed_output_kinds}.",
            f"Allowed action field kinds: {allowed_action_field_kinds}.",
            "",
            "UiOutput examples (JSON):",
            '- {"kind":"notice","level":"info","message":"Klar!"}',
            '- {"kind":"markdown","markdown":"## Resultat\\n\\nText..."}',
            '- {"kind":"table","title":"...","columns":[{"key":"k","label":"K"}],'
            ' "rows":[{"k":"v"}]}',
            '- {"kind":"json","title":"...","value":{"a":1}}',
            '- {"kind":"html_sandboxed","html":"<p>...</p>"}',
            "",
            "UiFormAction (next_actions) shape:",
            '- `{action_id, label, kind:"form", fields:[...]}`',
            "- Fields use `{name, label, kind, ...}` (and `options` for enum kinds).",
            "",
            "Limits (enforced by backend normalizer):",
            f"- max outputs: {caps.max_outputs}",
            f"- max next_actions: {caps.max_next_actions}",
            f"- max fields per action: {caps.max_fields_per_action}",
            f"- total ui_payload max: {_format_bytes(budgets.ui_payload_max_bytes)}",
            f"- state max: {_format_bytes(budgets.state_max_bytes)}",
            f"- notice.message max: {_format_bytes(caps.notice_message_max_bytes)}",
            f"- markdown max: {_format_bytes(caps.markdown_max_bytes)}",
            f"- html_sandboxed max: {_format_bytes(caps.html_sandboxed_max_bytes)}",
            (
                "- table caps: "
                f"{caps.table_max_cols} columns, {caps.table_max_rows} rows, "
                f"{_format_bytes(caps.table_cell_max_bytes)} per cell"
            ),
            (
                "- json caps: "
                f"{_format_bytes(caps.json_max_bytes)}, depth <= {caps.json_max_depth}, "
                f"{caps.json_max_keys} keys/object, {caps.json_max_array_len} items/array"
            ),
        ]
    )


def runner_constraints_fragment(*, settings: Settings) -> str:
    return "\n".join(
        [
            "## Runner constraints (execution environment)",
            "",
            "- Entrypoint: `def run_tool(input_dir: str, output_dir: str) -> dict`",
            "- No network access (Docker runs with `network_mode=none`).",
            "- Filesystem is read-only, except `/work` (input/output) and `/tmp`.",
            "- Artifacts must be written under `output_dir` (no absolute paths, no `..`).",
            "",
            "Resources:",
            f"- Timeout: {settings.RUNNER_TIMEOUT_SANDBOX_SECONDS}s (sandbox) / "
            f"{settings.RUNNER_TIMEOUT_PRODUCTION_SECONDS}s (production)",
            f"- CPU: {settings.RUNNER_CPU_LIMIT}",
            f"- Memory: {settings.RUNNER_MEMORY_LIMIT}",
        ]
    )


def helpers_fragment() -> str:
    return "\n".join(
        [
            "## Helpers (available in runner)",
            "",
            "- Prefer `skriptoteket_toolkit` helpers instead of parsing env JSON yourself:",
            "  - `read_inputs()` → initial form inputs (dict)",
            "  - `list_input_files()` → validated files from input manifest",
            "  - `get_action_parts()` → (action_id, action_input, state) for next_actions runs",
            "  - `read_settings()` → user saved settings from memory.json",
            "",
            "- `from tool_errors import ToolUserError` → raise a safe user-facing error "
            "(no stacktraces/paths/secrets).",
            "- `from pdf_helper import save_as_pdf` → `save_as_pdf(html, output_dir, filename)` "
            "(filename must end with `.pdf` and be relative under output).",
        ]
    )
