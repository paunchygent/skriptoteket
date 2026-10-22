"""Every paid AI call goes through HuleEdu's LLM provider door.

Purpose:
    Keep exam OpenAI traffic on the door's relayed routes (ST-SKRIPT-41-01):
    no module posts directly to OpenAI or OpenRouter, and only the door
    client owns httpx in the LLM lane. The script-editor providers still call
    OpenAI directly until TASK-SKRIPT-41-01-02 moves them; they are named below.
    Exam modules must never be allowlisted.

Relationships:
    - Scans ``src/skriptoteket/**/*.py`` and ``scripts/**/*.py``.
    - The door client is ``infrastructure/llm/door/client.py``.
"""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SRC_ROOT = ROOT / "src" / "skriptoteket"
SCRIPTS_ROOT = ROOT / "scripts"
DOOR_CLIENT = "src/skriptoteket/infrastructure/llm/door/client.py"
LLM_LANE = SRC_ROOT / "infrastructure" / "llm"

_DIRECT_URL_MARKERS = ("api.openai.com", "openrouter.ai", "/internal/v1/openai")

ALLOWLIST: dict[str, str] = {
    "src/skriptoteket/infrastructure/llm/openai/chat_stream_provider.py": (
        "script editor, TASK-SKRIPT-41-01-02"
    ),
    "src/skriptoteket/infrastructure/llm/openai/chat_ops_provider.py": (
        "script editor, TASK-SKRIPT-41-01-02"
    ),
    "src/skriptoteket/infrastructure/llm/openai/inline_completion_provider.py": (
        "script editor, TASK-SKRIPT-41-01-02"
    ),
    "scripts/llm_harness/inline_completion_harness.py": "script editor, TASK-SKRIPT-41-01-02",
}


def _string_literals(source: str) -> list[str]:
    tree = ast.parse(source)
    return [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    ]


def _direct_url_hits(source: str) -> list[str]:
    return sorted(
        {
            marker
            for text in _string_literals(source)
            for marker in _DIRECT_URL_MARKERS
            if marker in text
        }
    )


def _imports_httpx(source: str) -> bool:
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            if any(name.name == "httpx" or name.name.startswith("httpx.") for name in node.names):
                return True
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module == "httpx" or module.startswith("httpx."):
                return True
    return False


def _relative(path: Path) -> str:
    return str(path.relative_to(ROOT))


def _offending_url_modules() -> list[str]:
    offenders = []
    for base in (SRC_ROOT, SCRIPTS_ROOT):
        for path in sorted(base.rglob("*.py")):
            relative = _relative(path)
            if relative == DOOR_CLIENT or relative in ALLOWLIST:
                continue
            if _direct_url_hits(path.read_text(encoding="utf-8")):
                offenders.append(relative)
    return offenders


def _offending_httpx_modules() -> list[str]:
    offenders = []
    for path in sorted(LLM_LANE.rglob("*.py")):
        relative = _relative(path)
        if relative == DOOR_CLIENT or relative in ALLOWLIST:
            continue
        if _imports_httpx(path.read_text(encoding="utf-8")):
            offenders.append(relative)
    return offenders


def test_no_direct_openai_or_openrouter_urls_outside_the_door() -> None:
    assert _offending_url_modules() == []


def test_only_the_door_imports_httpx_in_the_llm_lane() -> None:
    assert _offending_httpx_modules() == []


def test_guard_flags_a_direct_openai_post() -> None:
    synthetic = (
        "import httpx\n"
        "\n"
        "async def complete(client: httpx.AsyncClient) -> None:\n"
        '    await client.post("https://api.openai.com/v1/responses", json={})\n'
    )

    assert _direct_url_hits(synthetic) == ["api.openai.com"]
    assert _imports_httpx(synthetic)
