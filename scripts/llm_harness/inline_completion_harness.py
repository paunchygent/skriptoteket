from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from importlib import resources
from pathlib import Path

import httpx

from skriptoteket.application.editor.ai_prompt import load_system_prompt_text
from skriptoteket.application.editor.prompt_composer import (
    PromptTemplateError,
    build_default_fragments,
    compose_system_prompt,
)
from skriptoteket.application.editor.prompt_templates import get_prompt_template
from skriptoteket.config import Settings
from skriptoteket.infrastructure.llm.openai.common import merge_headers, normalize_base_url
from skriptoteket.infrastructure.llm.openai.fim import build_fim_prompt
from skriptoteket.infrastructure.llm.openai.parsing import (
    extract_first_choice_delta,
    extract_response_stream_delta,
)
from skriptoteket.infrastructure.llm.openai.payloads import (
    build_chat_payload,
    build_responses_payload,
)
from skriptoteket.infrastructure.llm.token_counter_resolver import (
    SettingsBasedTokenCounterResolver,
)

DEFAULT_SLUGS = [
    "demo-settings-test",
    "demo-inputs",
    "demo-regression-table",
    "ist-vh-mejl-bcc",
]

SLUG_TO_FILENAME = {
    "demo-settings-test": "demo_settings_test.py",
    "demo-inputs": "demo_inputs.py",
    "demo-regression-table": "demo_regression_table.py",
    "ist-vh-mejl-bcc": "ist_vh_mejl_bcc.py",
}

SCENARIO_ORDER = [
    "finish_function",
    "indentation_insert",
    "spelling_correction",
    "inline_comment",
    "small_refactor",
]

GPT5_INSERT_INSTRUCTIONS = (
    "You are an IDE code completion engine. "
    "Output ONLY the code completion to insert at <CURSOR>. "
    "No markdown, no explanations, no surrounding quotes. "
    "Do NOT repeat the prefix or suffix. "
    "Keep the completion to <2 lines and when intent is 100% clear. "
    "If no good completion exists, output an empty string."
)

GPT5_STRUCTURED_INSTRUCTIONS = GPT5_INSERT_INSTRUCTIONS

STRUCTURED_INSERT_FORMAT = {
    "type": "json_schema",
    "name": "inline_completion_insert",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {"insert": {"type": "string"}},
        "required": ["insert"],
        "additionalProperties": False,
    },
}


@dataclass(frozen=True)
class ScriptFixture:
    slug: str
    filename: str
    source: str
    sha256: str


@dataclass(frozen=True)
class Scenario:
    slug: str
    name: str
    description: str
    prefix: str
    suffix: str
    cursor_indent: str
    language: str
    file_path: str
    expected_insert: str | None
    max_lines: int


@dataclass(frozen=True)
class SpellingSpec:
    needle: str
    drop_offset: int


@dataclass(frozen=True)
class LineSpec:
    line_contains: str


SPELLING_SPECS = {
    "demo-settings-test": SpellingSpec(
        needle='theme_color = settings.get("theme_color", "")',
        drop_offset=5,
    ),
    "demo-inputs": SpellingSpec(
        needle="output_root = Path(output_dir)",
        drop_offset=6,
    ),
    "demo-regression-table": SpellingSpec(
        needle='"title": "Regression table",',
        drop_offset=14,
    ),
    "ist-vh-mejl-bcc": SpellingSpec(
        needle="EMAIL_RE = re.compile",
        drop_offset=0,
    ),
}

COMMENT_SPECS = {
    "demo-settings-test": LineSpec(line_contains="settings = read_settings()"),
    "demo-inputs": LineSpec(line_contains="files = list_input_files()"),
    "demo-regression-table": LineSpec(line_contains='{"key": "10", "label": "Ten"'),
    "ist-vh-mejl-bcc": LineSpec(line_contains="SUPPORTED_INPUT_SUFFIXES ="),
}

REFACTOR_SPECS = {
    "demo-settings-test": LineSpec(line_contains='theme_color = settings.get("theme_color", "")'),
    "demo-inputs": LineSpec(line_contains="inputs = read_inputs()"),
    "demo-regression-table": LineSpec(line_contains='{"key": "2", "label": "Two"'),
    "ist-vh-mejl-bcc": LineSpec(line_contains="input_files = _select_input_files"),
}


def _utc_now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _load_fixture(slug: str) -> ScriptFixture:
    filename = SLUG_TO_FILENAME.get(slug)
    if not filename:
        raise ValueError(f"Unknown slug: {slug}")
    script_path = resources.files("skriptoteket.script_bank.scripts") / filename
    source = script_path.read_text(encoding="utf-8")
    return ScriptFixture(
        slug=slug,
        filename=filename,
        source=source,
        sha256=_sha256_text(source),
    )


def _leading_ws(line: str) -> str:
    return line[: len(line) - len(line.lstrip(" \t"))]


def _split_lines(text: str) -> list[str]:
    return text.splitlines(keepends=True)


def _find_run_tool_bounds(lines: list[str]) -> tuple[int, int, int, str]:
    def_idx = -1
    for idx, line in enumerate(lines):
        if line.lstrip().startswith("def run_tool"):
            def_idx = idx
            break
    if def_idx == -1:
        raise ValueError("run_tool definition not found")

    def_indent = _leading_ws(lines[def_idx])
    body_start = def_idx + 1
    while body_start < len(lines) and lines[body_start].strip() == "":
        body_start += 1

    body_end = body_start
    while body_end < len(lines):
        line = lines[body_end]
        if line.strip() == "":
            body_end += 1
            continue
        if len(_leading_ws(line)) <= len(def_indent):
            break
        body_end += 1

    return def_idx, body_start, body_end, def_indent


def _line_insert_payload(
    *,
    prefix_lines: list[str],
    removed_lines: list[str],
    suffix_lines: list[str],
) -> tuple[str, str, str, str]:
    if not removed_lines:
        raise ValueError("No removed lines to insert")
    first_line = removed_lines[0]
    indent = _leading_ws(first_line)
    stripped_first = first_line[len(indent) :]
    expected_lines = [stripped_first, *removed_lines[1:]]
    prefix = "".join(prefix_lines) + indent
    suffix = "".join(suffix_lines)
    expected = "".join(expected_lines)
    return prefix, suffix, expected, indent


def _build_finish_function(fixture: ScriptFixture) -> Scenario:
    lines = _split_lines(fixture.source)
    _def_idx, body_start, body_end, _def_indent = _find_run_tool_bounds(lines)
    body_lines = lines[body_start:body_end]
    if not body_lines:
        raise ValueError("run_tool body is empty")

    tail_count = min(12, max(4, len(body_lines) // 3))
    remove_start = max(body_start, body_end - tail_count)
    prefix, suffix, expected, indent = _line_insert_payload(
        prefix_lines=lines[:remove_start],
        removed_lines=lines[remove_start:body_end],
        suffix_lines=lines[body_end:],
    )

    return Scenario(
        slug=fixture.slug,
        name="finish_function",
        description="Complete the tail of run_tool.",
        prefix=prefix,
        suffix=suffix,
        cursor_indent=indent,
        language="Python",
        file_path="tool.py",
        expected_insert=expected,
        max_lines=48,
    )


def _build_indentation_insert(fixture: ScriptFixture) -> Scenario:
    lines = _split_lines(fixture.source)
    _def_idx, body_start, body_end, _def_indent = _find_run_tool_bounds(lines)

    opener_idx = None
    block_start = None
    block_end = None
    for idx in range(body_start, body_end - 1):
        line = lines[idx]
        if line.strip() == "":
            continue
        indent = _leading_ws(line)
        next_idx = idx + 1
        while next_idx < body_end and lines[next_idx].strip() == "":
            next_idx += 1
        if next_idx >= body_end:
            continue
        next_indent = _leading_ws(lines[next_idx])
        if len(next_indent) <= len(indent):
            continue
        if not line.rstrip().endswith((":", "[", "{", "(")):
            continue
        opener_idx = idx
        block_start = next_idx
        scan_idx = next_idx
        while scan_idx < body_end:
            if lines[scan_idx].strip() == "":
                scan_idx += 1
                continue
            if len(_leading_ws(lines[scan_idx])) <= len(indent):
                break
            scan_idx += 1
        block_end = scan_idx
        if block_end - block_start >= 1:
            break

    if opener_idx is None or block_start is None or block_end is None:
        raise ValueError("No suitable indented block found")

    remove_count = min(3, block_end - block_start)
    remove_start = block_start
    remove_end = block_start + remove_count

    prefix, suffix, expected, indent = _line_insert_payload(
        prefix_lines=lines[:remove_start],
        removed_lines=lines[remove_start:remove_end],
        suffix_lines=lines[remove_end:],
    )

    return Scenario(
        slug=fixture.slug,
        name="indentation_insert",
        description="Insert missing indented block lines.",
        prefix=prefix,
        suffix=suffix,
        cursor_indent=indent,
        language="Python",
        file_path="tool.py",
        expected_insert=expected,
        max_lines=12,
    )


def _build_spelling_correction(fixture: ScriptFixture) -> Scenario:
    spec = SPELLING_SPECS.get(fixture.slug)
    if spec is None:
        raise ValueError(f"Missing spelling spec for {fixture.slug}")

    source = fixture.source
    start = source.find(spec.needle)
    if start == -1:
        raise ValueError(f"Needle not found for spelling spec in {fixture.slug}")

    remove_pos = start + spec.drop_offset
    if remove_pos >= len(source):
        raise ValueError("Spelling drop position out of range")

    removed_char = source[remove_pos]
    prefix = source[:remove_pos]
    suffix = source[remove_pos + 1 :]

    return Scenario(
        slug=fixture.slug,
        name="spelling_correction",
        description="Insert missing character to fix spelling/identifier.",
        prefix=prefix,
        suffix=suffix,
        cursor_indent="",
        language="Python",
        file_path="tool.py",
        expected_insert=removed_char,
        max_lines=12,
    )


def _build_inline_comment(fixture: ScriptFixture) -> Scenario:
    spec = COMMENT_SPECS.get(fixture.slug)
    if spec is None:
        raise ValueError(f"Missing comment spec for {fixture.slug}")

    lines = _split_lines(fixture.source)
    line_idx = _find_line_index(lines, spec.line_contains)
    line = lines[line_idx]
    newline = "\n" if line.endswith("\n") else ""
    line_content = line[:-1] if newline else line

    prefix = "".join(lines[:line_idx]) + f"{line_content}  # "
    suffix = f"{newline}" + "".join(lines[line_idx + 1 :])
    indent = _leading_ws(line)

    return Scenario(
        slug=fixture.slug,
        name="inline_comment",
        description="Add an inline comment for the current line.",
        prefix=prefix,
        suffix=suffix,
        cursor_indent=indent,
        language="Python",
        file_path="tool.py",
        expected_insert=None,
        max_lines=12,
    )


def _build_small_refactor(fixture: ScriptFixture) -> Scenario:
    spec = REFACTOR_SPECS.get(fixture.slug)
    if spec is None:
        raise ValueError(f"Missing refactor spec for {fixture.slug}")

    lines = _split_lines(fixture.source)
    line_idx = _find_line_index(lines, spec.line_contains)

    prefix, suffix, expected, indent = _line_insert_payload(
        prefix_lines=lines[:line_idx],
        removed_lines=[lines[line_idx]],
        suffix_lines=lines[line_idx + 1 :],
    )

    return Scenario(
        slug=fixture.slug,
        name="small_refactor",
        description="Insert a missing local binding used later.",
        prefix=prefix,
        suffix=suffix,
        cursor_indent=indent,
        language="Python",
        file_path="tool.py",
        expected_insert=expected,
        max_lines=12,
    )


def _find_line_index(lines: list[str], needle: str) -> int:
    for idx, line in enumerate(lines):
        if needle in line:
            return idx
    raise ValueError(f"Line containing '{needle}' not found")


def _build_scenarios(slugs: list[str], *, filter_names: set[str] | None) -> list[Scenario]:
    scenarios: list[Scenario] = []
    builders = {
        "finish_function": _build_finish_function,
        "indentation_insert": _build_indentation_insert,
        "spelling_correction": _build_spelling_correction,
        "inline_comment": _build_inline_comment,
        "small_refactor": _build_small_refactor,
    }

    for slug in slugs:
        fixture = _load_fixture(slug)
        for name in SCENARIO_ORDER:
            if filter_names is not None and name not in filter_names:
                continue
            builder = builders[name]
            scenarios.append(builder(fixture))
    return scenarios


def _build_prompt_content(*, scenario: Scenario, include_max_lines: bool = True) -> str:
    max_lines_block = f"MaxLines: {scenario.max_lines}\n\n" if include_max_lines else ""
    return (
        f"Language: {scenario.language}\n"
        f"File: {scenario.file_path}\n"
        f"Slug: {scenario.slug}\n\n"
        f"{max_lines_block}"
        f"<PREFIX>\n{scenario.prefix}\n</PREFIX>\n\n"
        f"<SUFFIX>\n{scenario.suffix}\n</SUFFIX>\n\n"
        "<CURSOR>\nReturn only the insertion text."
    )


def _sanitize_headers(headers: dict[str, str]) -> dict[str, str]:
    sanitized = dict(headers)
    if "Authorization" in sanitized:
        sanitized["Authorization"] = "***"
    return sanitized


def _capture_root(settings: Settings, override: Path | None) -> Path:
    root = override or settings.ARTIFACTS_ROOT
    return root / "llm-captures" / "inline_completion_harness"


def _write_capture(root: Path, payload: dict[str, object]) -> Path:
    capture_id = str(uuid.uuid4())
    capture_dir = root / capture_id
    capture_dir.mkdir(parents=True, exist_ok=True)

    envelope = {
        "version": 1,
        "kind": "inline_completion_harness",
        "capture_id": capture_id,
        "captured_at": _utc_now_iso(),
        "payload": payload,
    }

    final_path = capture_dir / "capture.json"
    serialized = json.dumps(envelope, ensure_ascii=False, indent=2, sort_keys=True)

    tmp_file = tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=capture_dir,
        prefix="capture.",
        suffix=".tmp",
        delete=False,
    )
    try:
        tmp_file.write(serialized)
        tmp_file.flush()
        Path(tmp_file.name).replace(final_path)
    finally:
        try:
            Path(tmp_file.name).unlink(missing_ok=True)
        except OSError:
            pass

    return final_path


def _is_gpt5_nano(model: str) -> bool:
    model_lower = model.strip().lower()
    return model_lower.startswith("gpt-5-nano") or model_lower.startswith("openai/gpt-5-nano")


def _stream_responses(
    client: httpx.Client,
    *,
    url: str,
    headers: dict[str, str],
    payload: dict[str, object],
) -> tuple[str, list[dict[str, object]]]:
    events: list[dict[str, object]] = []
    completion = ""
    event_type: str | None = None

    with client.stream("POST", url, headers=headers, json=payload) as response:
        response.raise_for_status()
        for raw_line in response.iter_lines():
            if not raw_line:
                continue
            if raw_line.startswith("event:"):
                event_type = raw_line[6:].strip()
                events.append({"event": "event", "data": event_type})
                continue
            if not raw_line.startswith("data:"):
                events.append({"event": "line", "raw": raw_line})
                continue
            data = raw_line[5:].strip()
            if data == "[DONE]":
                events.append({"event": "done"})
                break
            try:
                payload_obj = json.loads(data)
            except json.JSONDecodeError:
                events.append({"event": "data", "raw": data, "parse_error": True})
                continue
            if not isinstance(payload_obj, dict):
                events.append({"event": "data", "raw": data})
                continue
            events.append({"event": event_type or "data", "data": payload_obj})
            delta, done = extract_response_stream_delta(payload_obj, event_type=event_type)
            if delta:
                completion += delta
            if done:
                break

    return completion, events


def _stream_chat_completions(
    client: httpx.Client,
    *,
    url: str,
    headers: dict[str, str],
    payload: dict[str, object],
) -> tuple[str, list[dict[str, object]]]:
    events: list[dict[str, object]] = []
    completion = ""

    with client.stream("POST", url, headers=headers, json=payload) as response:
        response.raise_for_status()
        for raw_line in response.iter_lines():
            if not raw_line:
                continue
            if not raw_line.startswith("data:"):
                events.append({"event": "line", "raw": raw_line})
                continue
            data = raw_line[5:].strip()
            if data == "[DONE]":
                events.append({"event": "done"})
                break
            try:
                payload_obj = json.loads(data)
            except json.JSONDecodeError:
                events.append({"event": "data", "raw": data, "parse_error": True})
                continue
            if not isinstance(payload_obj, dict):
                events.append({"event": "data", "raw": data})
                continue
            events.append({"event": "data", "data": payload_obj})
            try:
                delta, _finish_reason = extract_first_choice_delta(payload_obj)
            except ValueError:
                continue
            if delta:
                completion += delta

    return completion, events


def _compute_duplication_ratio(prefix: str, completion: str) -> float:
    completion_lines = [line.strip() for line in completion.splitlines() if line.strip()]
    if not completion_lines:
        return 0.0
    prefix_lines = {line.strip() for line in prefix.splitlines() if line.strip()}
    duplicated = sum(1 for line in completion_lines if line in prefix_lines)
    return duplicated / len(completion_lines)


def _compute_cursor_overlap_chars(prefix: str, completion: str) -> int:
    if not prefix or not completion:
        return 0
    max_len = min(len(prefix), len(completion))
    for size in range(max_len, 0, -1):
        if completion.startswith(prefix[-size:]):
            return size
    return 0


def _detect_prefix_echo(prefix: str, completion: str) -> bool:
    completion_lines = [line for line in completion.splitlines() if line.strip()]
    if len(completion_lines) < 3:
        return False
    prefix_text = prefix
    for idx in range(len(completion_lines) - 2):
        chunk = "\n".join(completion_lines[idx : idx + 3])
        if chunk and chunk in prefix_text:
            return True
    return False


def _indentation_match(cursor_indent: str, completion: str) -> bool | None:
    if not cursor_indent or not completion.strip():
        return None
    for line in completion.splitlines():
        if not line.strip():
            continue
        return line.startswith(cursor_indent)
    return None


def _context_alignment(prefix: str, completion: str) -> bool | None:
    if not completion:
        return None
    cursor_at_line_start = prefix.endswith("\n") or prefix.endswith("\r\n")
    if cursor_at_line_start:
        return True
    return not completion.startswith("\n")


def _compute_metrics(scenario: Scenario, completion: str) -> dict[str, object]:
    line_count = len([line for line in completion.splitlines() if line.strip()])
    max_lines = scenario.max_lines
    cursor_overlap_chars = _compute_cursor_overlap_chars(scenario.prefix, completion)
    metrics = {
        "line_count": line_count,
        "max_lines_allowed": max_lines,
        "line_count_ok": line_count <= max_lines,
        "duplication_ratio": round(_compute_duplication_ratio(scenario.prefix, completion), 4),
        "prefix_echo": _detect_prefix_echo(scenario.prefix, completion),
        "cursor_overlap_chars": cursor_overlap_chars,
        "cursor_overlap_ok": cursor_overlap_chars == 0,
        "indentation_match": _indentation_match(scenario.cursor_indent, completion),
        "context_alignment": _context_alignment(scenario.prefix, completion),
    }
    return metrics


def _resolve_local_model(client: httpx.Client, base_url: str, override: str | None) -> str:
    if override:
        return override
    response = client.get(f"{base_url}/models")
    response.raise_for_status()
    payload = response.json()
    data = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(data, list) or not data:
        raise ValueError("Local /models returned no models")
    model_id = data[0].get("id")
    if not isinstance(model_id, str) or not model_id:
        raise ValueError("Local /models missing model id")
    return model_id


def _build_gpt5_payload(
    *,
    model: str,
    scenario: Scenario,
    max_tokens: int,
    variant: str,
    developer_prompt: str | None,
) -> tuple[dict[str, object], str, str]:
    instructions = (
        GPT5_STRUCTURED_INSTRUCTIONS if variant == "structured" else GPT5_INSERT_INSTRUCTIONS
    )
    if developer_prompt:
        instructions = f"{developer_prompt}\n\n{instructions}"
    content = _build_prompt_content(scenario=scenario, include_max_lines=False)
    text_format = STRUCTURED_INSERT_FORMAT if variant == "structured" else None

    payload = build_responses_payload(
        model=model,
        messages=[{"role": "user", "content": content}],
        instructions=instructions,
        max_tokens=max_tokens,
        temperature=0,
        reasoning_effort="minimal",
        text_verbosity="low",
        stream=True,
        text_format=text_format,
    )
    payload["store"] = False
    payload["truncation"] = "auto"
    return payload, instructions, content


def _build_local_payload(
    *,
    model: str,
    scenario: Scenario,
    max_tokens: int,
    system_prompt: str,
    temperature: float,
) -> tuple[dict[str, object], str]:
    user_prompt = build_fim_prompt(
        prefix=scenario.prefix,
        suffix=scenario.suffix,
        model=model,
    )
    payload = build_chat_payload(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=max_tokens,
        temperature=temperature,
        reasoning_effort=None,
        stream=True,
        stop=["\n```"],
    )
    return payload, user_prompt


def _parse_structured_insert(text: str) -> tuple[str, str | None]:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        return text, f"json_decode_error: {exc}"
    if not isinstance(payload, dict):
        return text, "json_not_object"
    insert = payload.get("insert")
    if not isinstance(insert, str):
        return text, "missing_insert_field"
    return insert, None


def _compose_system_prompt_unchecked(*, settings: Settings) -> str:
    template = get_prompt_template(template_id=settings.LLM_COMPLETION_TEMPLATE_ID)
    template_text = load_system_prompt_text(prompt_path=template.template_path)
    fragments = build_default_fragments(settings=settings)
    for placeholder, fragment in fragments.items():
        template_text = template_text.replace(f"{{{{{placeholder}}}}}", fragment)
    return template_text


def _load_system_prompt(settings: Settings, model: str, *, allow_oversize: bool = False) -> str:
    resolver = SettingsBasedTokenCounterResolver(settings=settings)
    token_counter = resolver.for_model(model=model)
    try:
        composed = compose_system_prompt(
            template_id=settings.LLM_COMPLETION_TEMPLATE_ID,
            settings=settings,
            token_counter=token_counter,
        )
        return composed.text
    except PromptTemplateError:
        if not allow_oversize:
            raise
        return _compose_system_prompt_unchecked(settings=settings)


def _estimate_structured_overhead_tokens(*, token_counter, insert_text: str | None) -> int:
    base_text = insert_text or ""
    json_text = json.dumps({"insert": base_text}, ensure_ascii=False)
    base_tokens = token_counter.count_text(base_text) if base_text else 0
    json_tokens = token_counter.count_text(json_text)
    overhead = json_tokens - base_tokens
    return overhead if overhead > 0 else 0


def _estimate_structured_required_tokens(*, token_counter, insert_text: str | None) -> int:
    json_text = json.dumps({"insert": insert_text or ""}, ensure_ascii=False)
    return token_counter.count_text(json_text)


def _build_timeout(seconds: float) -> httpx.Timeout:
    return httpx.Timeout(connect=10.0, read=seconds, write=10.0, pool=10.0)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inline completion harness (GPT-5-nano + local FIM)."
    )
    parser.add_argument("--slugs", nargs="*", default=DEFAULT_SLUGS)
    parser.add_argument("--scenarios", nargs="*", choices=SCENARIO_ORDER)
    parser.add_argument("--providers", choices=["gpt5", "local", "all"], default="gpt5")
    parser.add_argument("--variants", choices=["delimiter", "structured", "all"], default="all")
    parser.add_argument("--max-output-tokens", nargs="*", type=int, default=[64, 128])
    parser.add_argument(
        "--structured-budgeting",
        choices=["on", "off"],
        default="on",
        help="Enable/disable extra token budgeting for structured outputs.",
    )
    parser.add_argument(
        "--gpt5-include-fim-prompt",
        action="store_true",
        help="Include the full inline completion system prompt (FIM shards) in GPT-5 instructions.",
    )
    parser.add_argument(
        "--allow-oversize-system-prompt",
        action="store_true",
        help="Allow system prompt composition to exceed the configured token budget.",
    )
    parser.add_argument("--openai-base-url")
    parser.add_argument("--openai-api-key")
    parser.add_argument("--openai-model", default="gpt-5-nano")
    parser.add_argument("--local-base-url")
    parser.add_argument("--local-model")
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--artifacts-root", type=Path)
    parser.add_argument("--dry-run", action="store_true")

    args = parser.parse_args()
    settings = Settings()

    filter_names = set(args.scenarios) if args.scenarios else None
    scenarios = _build_scenarios(list(args.slugs), filter_names=filter_names)

    providers: list[str]
    if args.providers == "all":
        providers = ["gpt5", "local"]
    else:
        providers = [args.providers]

    variants: list[str]
    if args.variants == "all":
        variants = ["delimiter", "structured"]
    else:
        variants = [args.variants]

    structured_budgeting = args.structured_budgeting == "on"

    max_tokens_list = [int(value) for value in args.max_output_tokens if int(value) > 0]
    if not max_tokens_list:
        raise SystemExit("Provide at least one --max-output-tokens value")

    capture_root = _capture_root(settings, args.artifacts_root)
    capture_root.mkdir(parents=True, exist_ok=True)

    if args.dry_run:
        print(f"scenarios={len(scenarios)}")
        for scenario in scenarios:
            print(f"- {scenario.slug}:{scenario.name}")
        return 0

    run_id = str(uuid.uuid4())

    timeout = _build_timeout(args.timeout)
    client = httpx.Client(timeout=timeout)

    openai_base_url = normalize_base_url(
        base_url=args.openai_base_url
        or settings.LLM_COMPLETION_FALLBACK_BASE_URL
        or "https://api.openai.com/v1",
    )
    openai_api_key = (
        args.openai_api_key
        or settings.OPENAI_LLM_COMPLETION_API_KEY
        or settings.OPENAI_LLM_CHAT_API_KEY
    ).strip()

    local_base_url = normalize_base_url(
        base_url=args.local_base_url or settings.LLM_COMPLETION_BASE_URL
    )

    local_model: str | None = None
    if "local" in providers:
        local_model = _resolve_local_model(client, local_base_url, args.local_model)

    local_system_prompt = None
    local_temperature = settings.LLM_COMPLETION_TEMPERATURE
    if "local" in providers and local_model:
        local_system_prompt = _load_system_prompt(
            settings,
            local_model,
            allow_oversize=args.allow_oversize_system_prompt,
        )

    gpt5_token_counter = None
    if "gpt5" in providers:
        gpt5_token_counter = SettingsBasedTokenCounterResolver(settings=settings).for_model(
            model=args.openai_model
        )
    gpt5_developer_prompt = None
    if "gpt5" in providers and args.gpt5_include_fim_prompt:
        gpt5_developer_prompt = _load_system_prompt(
            settings=settings,
            model=settings.LLM_COMPLETION_MODEL,
            allow_oversize=args.allow_oversize_system_prompt,
        )

    try:
        for scenario in scenarios:
            for max_tokens in max_tokens_list:
                if "gpt5" in providers:
                    if not openai_api_key:
                        raise SystemExit("OPENAI API key is required for gpt5 provider")
                    for variant in variants:
                        json_overhead_tokens = 0
                        required_json_tokens = 0
                        upper_bound_tokens = 0
                        effective_max_tokens = max_tokens
                        if (
                            variant == "structured"
                            and gpt5_token_counter is not None
                            and structured_budgeting
                        ):
                            json_overhead_tokens = _estimate_structured_overhead_tokens(
                                token_counter=gpt5_token_counter,
                                insert_text=scenario.expected_insert,
                            )
                            required_json_tokens = _estimate_structured_required_tokens(
                                token_counter=gpt5_token_counter,
                                insert_text=scenario.expected_insert,
                            )
                            upper_bound_tokens = _estimate_structured_required_tokens(
                                token_counter=gpt5_token_counter,
                                insert_text=scenario.prefix + scenario.suffix,
                            )
                            effective_max_tokens = max_tokens + json_overhead_tokens
                            if required_json_tokens > 0:
                                effective_max_tokens = max(
                                    effective_max_tokens,
                                    required_json_tokens + 4,
                                )
                            if upper_bound_tokens > 0:
                                effective_max_tokens = max(
                                    effective_max_tokens,
                                    upper_bound_tokens + 4,
                                )

                        payload, instructions, content = _build_gpt5_payload(
                            model=args.openai_model,
                            scenario=scenario,
                            max_tokens=effective_max_tokens,
                            variant=variant,
                            developer_prompt=gpt5_developer_prompt,
                        )
                        url = f"{openai_base_url}/responses"
                        headers = merge_headers(api_key=openai_api_key, extra_headers={})

                        completion = ""
                        events: list[dict[str, object]]
                        error: dict[str, object] | None = None
                        try:
                            completion, events = _stream_responses(
                                client,
                                url=url,
                                headers=headers,
                                payload=payload,
                            )
                        except Exception as exc:  # noqa: BLE001 - harness capture
                            events = []
                            error = {
                                "type": type(exc).__name__,
                                "message": str(exc),
                            }

                        parsed_completion = completion
                        parse_error = None
                        if variant == "structured":
                            parsed_completion, parse_error = _parse_structured_insert(completion)

                        metrics = _compute_metrics(scenario, parsed_completion)
                        payload_record = {
                            "run_id": run_id,
                            "provider": "gpt5",
                            "variant": variant,
                            "model": args.openai_model,
                            "slug": scenario.slug,
                            "scenario": scenario.name,
                            "params": {
                                "max_output_tokens": max_tokens,
                                "max_output_tokens_effective": effective_max_tokens,
                                "json_overhead_tokens": json_overhead_tokens,
                                "json_required_tokens": required_json_tokens,
                                "json_upper_bound_tokens": upper_bound_tokens,
                                "reasoning_effort": "minimal",
                                "text_verbosity": "low",
                                "stream": True,
                                "store": False,
                                "truncation": "auto",
                            },
                            "fixture": {
                                "file_path": scenario.file_path,
                                "language": scenario.language,
                                "source_hash": _sha256_text(scenario.prefix + scenario.suffix),
                            },
                            "prompt": {
                                "instructions": instructions,
                                "content": content,
                            },
                            "request": {
                                "url": url,
                                "headers": _sanitize_headers(headers),
                                "payload": payload,
                            },
                            "response": {
                                "raw_completion": completion,
                                "parsed_completion": parsed_completion,
                                "parse_error": parse_error,
                                "events": events,
                                "error": error,
                            },
                            "expected_insert": scenario.expected_insert,
                            "metrics": metrics,
                        }
                        capture_path = _write_capture(capture_root, payload_record)
                        print(f"captured={capture_path}")

                if "local" in providers:
                    if local_model is None or local_system_prompt is None:
                        raise SystemExit("Local model/system prompt unavailable")

                    payload, user_prompt = _build_local_payload(
                        model=local_model,
                        scenario=scenario,
                        max_tokens=max_tokens,
                        system_prompt=local_system_prompt,
                        temperature=local_temperature,
                    )
                    url = f"{local_base_url}/chat/completions"
                    headers = merge_headers(api_key="", extra_headers={})

                    completion = ""
                    events = []
                    error = None
                    try:
                        completion, events = _stream_chat_completions(
                            client,
                            url=url,
                            headers=headers,
                            payload=payload,
                        )
                    except Exception as exc:  # noqa: BLE001 - harness capture
                        error = {"type": type(exc).__name__, "message": str(exc)}

                    metrics = _compute_metrics(scenario, completion)
                    payload_record = {
                        "run_id": run_id,
                        "provider": "local",
                        "variant": "fim",
                        "model": local_model,
                        "slug": scenario.slug,
                        "scenario": scenario.name,
                        "params": {
                            "max_tokens": max_tokens,
                            "stream": True,
                            "temperature": local_temperature,
                        },
                        "fixture": {
                            "file_path": scenario.file_path,
                            "language": scenario.language,
                            "source_hash": _sha256_text(scenario.prefix + scenario.suffix),
                        },
                        "prompt": {
                            "system": local_system_prompt,
                            "fim_user": user_prompt,
                        },
                        "request": {
                            "url": url,
                            "headers": _sanitize_headers(headers),
                            "payload": payload,
                        },
                        "response": {
                            "completion": completion,
                            "events": events,
                            "error": error,
                        },
                        "expected_insert": scenario.expected_insert,
                        "metrics": metrics,
                    }
                    capture_path = _write_capture(capture_root, payload_record)
                    print(f"captured={capture_path}")

        return 0
    finally:
        client.close()


if __name__ == "__main__":
    raise SystemExit(main())
