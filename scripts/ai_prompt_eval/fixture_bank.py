"""Repo-owned fixture bank for AI prompt evaluation (non-sensitive).

Fixtures include synthetic editor contexts (prefix/suffix/selection/instruction) intended to
exercise prompt composition, budgeting, and llama.cpp behavior through the real HTTP pipeline.

Important: This module may contain code-like strings, but they must be non-sensitive and must
never be written to `.artifacts/` by the harness (artifacts are metadata-only).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

PromptEvalOutcome = Literal["ok", "empty", "truncated", "over_budget", "timeout", "error"]


class InlineCompletionFixture(BaseModel):
    model_config = ConfigDict(frozen=True)

    fixture_id: str = Field(min_length=1)
    capability: Literal["inline_completion"] = "inline_completion"
    language: Literal["python"] = "python"
    prefix: str
    suffix: str
    allowed_outcomes: frozenset[PromptEvalOutcome] | None = None


class EditSuggestionFixture(BaseModel):
    model_config = ConfigDict(frozen=True)

    fixture_id: str = Field(min_length=1)
    capability: Literal["edit_suggestion"] = "edit_suggestion"
    language: Literal["python"] = "python"
    prefix: str
    selection: str
    suffix: str
    instruction: str | None = None
    allowed_outcomes: frozenset[PromptEvalOutcome] | None = None


PromptEvalFixture = InlineCompletionFixture | EditSuggestionFixture


def _repeat_lines(line: str, count: int) -> str:
    return "\n".join([line] * count) + ("\n" if count else "")


def _python_prelude() -> str:
    return "\n".join(
        [
            "import json",
            "import os",
            "from pathlib import Path",
            "",
            "",
            "def _load_manifest() -> list[Path]:",
            '    manifest = json.loads(os.environ.get("SKRIPTOTEKET_INPUT_MANIFEST", "{}"))',
            '    files = manifest.get("files", [])',
            '    return [Path(f["path"]) for f in files if "path" in f]',
            "",
            "",
        ]
    )


FIXTURES: tuple[PromptEvalFixture, ...] = (
    InlineCompletionFixture(
        fixture_id="inline_small_cursor_in_run_tool",
        prefix="\n".join(
            [
                _python_prelude(),
                "",
                "",
                "def run_tool(input_dir: str, output_dir: str) -> dict:",
                "    files = _load_manifest()",
                "    path = files[0] if files else None",
                "    if path is None:",
                "        return {",
                '            "outputs": [{"kind": "notice", "level": "error", "message": "Ingen fil uppladdad"}],',
                '            "next_actions": [],',
                '            "state": None,',
                "        }",
                "",
                '    text = path.read_text(encoding="utf-8")',
                "    # TODO: parse the file and build a small summary",
                "    ",
            ]
        ),
        suffix="\n".join(
            [
                "",
                "    return {",
                '        "outputs": [{"kind": "markdown", "markdown": "## Resultat\\n\\n..."}],',
                '        "next_actions": [],',
                '        "state": None,',
                "    }",
                "",
            ]
        ),
    ),
    InlineCompletionFixture(
        fixture_id="inline_suffix_heavy_existing_tool",
        prefix="\n".join(
            [
                _python_prelude(),
                "",
                "def run_tool(input_dir: str, output_dir: str) -> dict:",
                "    # Cursor is at the top of a large existing function.",
                "    ",
            ]
        ),
        suffix="\n".join(
            [
                "",
                "    files = _load_manifest()",
                "    path = files[0] if files else None",
                "    if path is None:",
                "        return {",
                '            "outputs": [{"kind": "notice", "level": "error", "message": "Ingen fil uppladdad"}],',
                '            "next_actions": [],',
                '            "state": None,',
                "        }",
                "",
                "    data = path.read_bytes()",
                "    size = len(data)",
                "    lines = data.splitlines()",
                "    return {",
                '        "outputs": [',
                '            {"kind": "table", "title": "Metadata", "columns": [{"key": "k", "label": "Nyckel"}, {"key": "v", "label": "Värde"}],',
                '             "rows": [{"k": "bytes", "v": str(size)}, {"k": "rader", "v": str(len(lines))}]}',
                "        ],",
                '        "next_actions": [],',
                '        "state": None,',
                "    }",
                "",
                _repeat_lines("# Existing implementation detail line", 120),
            ]
        ),
    ),
    InlineCompletionFixture(
        fixture_id="inline_large_prefix_many_helpers",
        prefix="\n".join(
            [
                _repeat_lines("def _helper() -> int: return 1", 200),
                "",
                "def run_tool(input_dir: str, output_dir: str) -> dict:",
                "    # Intentionally large prefix to exercise trimming/budgeting.",
                "    ",
            ]
        ),
        suffix="",
    ),
    InlineCompletionFixture(
        fixture_id="inline_contract_output_table_rows",
        prefix="\n".join(
            [
                _python_prelude(),
                "",
                "def run_tool(input_dir: str, output_dir: str) -> dict:",
                "    files = _load_manifest()",
                "    path = files[0] if files else None",
                "    if path is None:",
                "        return {",
                '            "outputs": [{"kind": "notice", "level": "error", "message": "Ingen fil uppladdad"}],',
                '            "next_actions": [],',
                '            "state": None,',
                "        }",
                "",
                "    rows = []",
                "    # TODO: populate rows with (line_no, text) for the first 5 lines",
                "    ",
            ]
        ),
        suffix="\n".join(
            [
                "",
                "    return {",
                '        "outputs": [',
                '            {"kind": "table", "title": "Förhandsvisning",',
                '             "columns": [{"key": "line", "label": "Rad"}, {"key": "text", "label": "Text"}],',
                '             "rows": rows},',
                "        ],",
                '        "next_actions": [],',
                '        "state": None,',
                "    }",
                "",
            ]
        ),
    ),
    InlineCompletionFixture(
        fixture_id="inline_swedish_user_message_from_english_comment",
        prefix="\n".join(
            [
                _python_prelude(),
                "",
                "def run_tool(input_dir: str, output_dir: str) -> dict:",
                "    files = _load_manifest()",
                "    path = files[0] if files else None",
                "    if path is None:",
                "        # TODO: return a Swedish notice message (no English)",
                "        ",
            ]
        ),
        suffix="",
    ),
    EditSuggestionFixture(
        fixture_id="edit_translate_notice_to_swedish",
        instruction="Översätt felmeddelandet till tydlig svenska.",
        prefix="def run_tool(input_dir: str, output_dir: str) -> dict:\n",
        selection="\n".join(
            [
                "    if path is None:",
                "        return {",
                '            "outputs": [{"kind": "notice", "level": "error", "message": "No file uploaded"}],',
                '            "next_actions": [],',
                '            "state": None,',
                "        }",
            ]
        )
        + "\n",
        suffix="",
    ),
    EditSuggestionFixture(
        fixture_id="edit_fix_contract_kind_html_to_html_sandboxed",
        instruction="Fixa output-kinden så att den följer Contract v2 (html_sandboxed).",
        prefix="def run_tool(input_dir: str, output_dir: str) -> dict:\n",
        selection="\n".join(
            [
                "    return {",
                '        "outputs": [{"kind": "html", "html": "<p>Hej</p>"}],',
                '        "next_actions": [],',
                '        "state": None,',
                "    }",
            ]
        )
        + "\n",
        suffix="",
    ),
    EditSuggestionFixture(
        fixture_id="edit_large_selection_budget_stress",
        instruction="Gör koden mer robust och lägg till en svensk sammanfattning i outputs.",
        prefix=_python_prelude()
        + "\n"
        + "def run_tool(input_dir: str, output_dir: str) -> dict:\n"
        + "    files = _load_manifest()\n"
        + "    path = files[0] if files else None\n"
        + "    if path is None:\n"
        + "        return {\n"
        + '            "outputs": [{"kind": "notice", "level": "error", "message": "Ingen fil uppladdad"}],\n'
        + '            "next_actions": [],\n'
        + '            "state": None,\n'
        + "        }\n\n",
        selection=_repeat_lines("    value = value + 1  # tight loop", 800),
        suffix="\n".join(
            [
                "",
                "    return {",
                '        "outputs": [],',
                '        "next_actions": [],',
                '        "state": None,',
                "    }",
                "",
            ]
        ),
        allowed_outcomes=frozenset({"ok", "empty", "truncated", "over_budget", "timeout", "error"}),
    ),
    EditSuggestionFixture(
        fixture_id="edit_suffix_heavy_context",
        instruction="Rensa bort onödiga rader och gör variabelnamn tydligare.",
        prefix="def run_tool(input_dir: str, output_dir: str) -> dict:\n",
        selection="\n".join(
            [
                "    rows = []",
                "    for i in range(10):",
                "        rows.append({'line': i, 'text': str(i)})",
                "    return {",
                '        "outputs": [{"kind": "table", "title": "Rader", "columns": [{"key": "line", "label": "Rad"}, {"key": "text", "label": "Text"}], "rows": rows}],',
                '        "next_actions": [],',
                '        "state": None,',
                "    }",
            ]
        )
        + "\n",
        suffix=_repeat_lines("# lots of trailing context after selection", 160),
    ),
)


def get_fixture(*, fixture_id: str) -> PromptEvalFixture:
    for fixture in FIXTURES:
        if fixture.fixture_id == fixture_id:
            return fixture
    raise KeyError(f"Unknown fixture_id: {fixture_id}")
