from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


def _ensure_repo_root_on_path() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    repo_root_str = str(repo_root)
    src_root_str = str(repo_root / "src")
    if repo_root_str not in sys.path:
        sys.path.insert(0, repo_root_str)
    if src_root_str not in sys.path:
        sys.path.insert(0, src_root_str)


_ensure_repo_root_on_path()

from scripts.ai_prompt_eval.kodassistent_eval_checks import (  # noqa: E402
    validate_diff,
    validate_review,
)
from scripts.ai_prompt_eval.llama_client import (  # noqa: E402
    LlamaClientError,
    extract_text,
    extract_usage,
    send_chat_completion,
    wait_for_health,
)


@dataclass(frozen=True)
class EvalConfig:
    prompt_dir: Path
    base_url: str
    model: str
    temperature: float
    max_tokens: int
    timeout_seconds: float
    health_timeout_seconds: float
    skip_health: bool
    output_dir: Path
    label: str
    system_template: str
    system_prompt_path: Path | None
    no_system: bool
    token_count_model: str
    tool_diff_prompt: str
    schema_diff_prompt: str
    skip_schema_diff: bool


def _utc_run_id() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _parse_args() -> EvalConfig:
    parser = argparse.ArgumentParser(
        description="Run the Kodassistenten eval against a local llama.cpp server.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--prompt-dir",
        default=(
            "docs/reference/reports/artifacts/llama-kodassistent-eval-v2/"
            "llama-kodassistent-eval-v2-20260131T150000Z"
        ),
        help="Directory containing prompt1_review_kodassistent_v2.txt and diff prompts.",
    )
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8082",
        help="llama.cpp base URL.",
    )
    parser.add_argument(
        "--model",
        default="local",
        help="Model name passed to the server (llama.cpp ignores this for local).",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.1,
        help="Sampling temperature.",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=1400,
        help="Maximum tokens to generate.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=240.0,
        help="Request timeout in seconds.",
    )
    parser.add_argument(
        "--health-timeout-seconds",
        type=float,
        default=120.0,
        help="Max seconds to wait for /health.",
    )
    parser.add_argument(
        "--skip-health",
        action="store_true",
        help="Skip waiting for /health to return ok.",
    )
    parser.add_argument(
        "--output-root",
        default=".artifacts/llama-kodassistent-eval-v2",
        help="Root folder for run artifacts.",
    )
    parser.add_argument(
        "--output-dir",
        help="Explicit output directory (skips auto timestamp).",
    )
    parser.add_argument(
        "--label",
        default="run",
        help="Label prefix for output files (e.g., glm/devstral).",
    )
    parser.add_argument(
        "--system-template",
        default="editor_chat_v1",
        help="Prompt template id used to build the system message.",
    )
    parser.add_argument(
        "--system-prompt-path",
        help="Override system prompt with a file path (skips template composition).",
    )
    parser.add_argument(
        "--no-system",
        action="store_true",
        help="Disable system prompt injection.",
    )
    parser.add_argument(
        "--token-count-model",
        default="local",
        help="Model name used to estimate system prompt token budget.",
    )
    parser.add_argument(
        "--tool-diff-prompt",
        default="prompt2_diff_tool_kodassistent_v2.txt",
        help="Prompt filename for the tool.py diff step.",
    )
    parser.add_argument(
        "--schema-diff-prompt",
        default="prompt3_diff_schema_kodassistent_v2.txt",
        help="Prompt filename for the schema/usage diff step.",
    )
    parser.add_argument(
        "--skip-schema-diff",
        action="store_true",
        help="Skip the schema/usage diff step.",
    )
    args = parser.parse_args()

    prompt_dir = Path(args.prompt_dir)
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        run_id = _utc_run_id()
        output_dir = Path(args.output_root) / f"llama-kodassistent-eval-v2-{run_id}"

    return EvalConfig(
        prompt_dir=prompt_dir,
        base_url=args.base_url.rstrip("/"),
        model=args.model,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
        timeout_seconds=args.timeout_seconds,
        health_timeout_seconds=args.health_timeout_seconds,
        skip_health=args.skip_health,
        output_dir=output_dir,
        label=args.label,
        system_template=args.system_template,
        system_prompt_path=Path(args.system_prompt_path) if args.system_prompt_path else None,
        no_system=args.no_system,
        token_count_model=args.token_count_model,
        tool_diff_prompt=args.tool_diff_prompt,
        schema_diff_prompt=args.schema_diff_prompt,
        skip_schema_diff=args.skip_schema_diff,
    )


def _load_prompt(prompt_dir: Path, name: str) -> str:
    path = prompt_dir / name
    if not path.exists():
        raise FileNotFoundError(f"Missing prompt file: {path}")
    return path.read_text(encoding="utf-8")


def _build_system_prompt(config: EvalConfig) -> str | None:
    if config.no_system:
        return None
    if config.system_prompt_path is not None:
        return config.system_prompt_path.read_text(encoding="utf-8")

    try:
        from skriptoteket.application.editor.prompt_composer import compose_system_prompt
        from skriptoteket.config import Settings
        from skriptoteket.infrastructure.llm.token_counter_resolver import (
            SettingsBasedTokenCounterResolver,
        )
    except ModuleNotFoundError as exc:
        raise LlamaClientError(
            "System prompt composition requires app dependencies. "
            "Either install them or pass --system-prompt-path / --no-system."
        ) from exc

    settings = Settings()
    token_counter = SettingsBasedTokenCounterResolver(settings=settings).for_model(
        model=config.token_count_model
    )
    try:
        composed = compose_system_prompt(
            template_id=config.system_template,
            settings=settings,
            token_counter=token_counter,
        )
    except Exception as exc:  # noqa: BLE001 - surface prompt composition failures
        raise LlamaClientError(f"System prompt composition failed: {exc}") from exc
    return composed.text


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _read_json_if_exists(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _run_step(
    *,
    config: EvalConfig,
    step: str,
    prompt_name: str,
    system_prompt: str | None,
) -> tuple[dict, str]:
    prompt = _load_prompt(config.prompt_dir, prompt_name)
    raw = send_chat_completion(
        prompt=prompt,
        base_url=config.base_url,
        model=config.model,
        temperature=config.temperature,
        max_tokens=config.max_tokens,
        timeout_seconds=config.timeout_seconds,
        system_prompt=system_prompt,
    )
    try:
        response_json = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise LlamaClientError(f"Invalid JSON response for {step}: {exc}") from exc
    text = extract_text(response_json)

    response_path = config.output_dir / f"{config.label}_{step}.response.json"
    response_path.parent.mkdir(parents=True, exist_ok=True)
    response_path.write_bytes(raw)

    text_path = config.output_dir / f"{config.label}_{step}.text"
    text_path.write_text(text, encoding="utf-8")

    usage = extract_usage(response_json)
    return usage, text


def main() -> int:
    config = _parse_args()
    config.output_dir.mkdir(parents=True, exist_ok=True)

    meta = {
        "prompt_dir": str(config.prompt_dir),
        "base_url": config.base_url,
        "model": config.model,
        "temperature": config.temperature,
        "max_tokens": config.max_tokens,
        "timeout_seconds": config.timeout_seconds,
        "label": config.label,
        "system_template": None if config.no_system else config.system_template,
        "system_prompt_path": str(config.system_prompt_path) if config.system_prompt_path else None,
        "token_count_model": config.token_count_model,
        "tool_diff_prompt": config.tool_diff_prompt,
        "schema_diff_prompt": None if config.skip_schema_diff else config.schema_diff_prompt,
    }
    _write_json(config.output_dir / f"{config.label}_run_meta.json", meta)

    try:
        if not config.skip_health:
            wait_for_health(
                base_url=config.base_url,
                timeout_seconds=config.health_timeout_seconds,
            )

        system_prompt = _build_system_prompt(config)
        review_usage, review_text = _run_step(
            config=config,
            step="review",
            prompt_name="prompt1_review_kodassistent_v2.txt",
            system_prompt=system_prompt,
        )
        tool_diff_usage, tool_diff_text = _run_step(
            config=config,
            step="diff_tool",
            prompt_name=config.tool_diff_prompt,
            system_prompt=system_prompt,
        )
        schema_diff_usage = None
        schema_diff_text = ""
        if not config.skip_schema_diff:
            schema_diff_usage, schema_diff_text = _run_step(
                config=config,
                step="diff_schema",
                prompt_name=config.schema_diff_prompt,
                system_prompt=system_prompt,
            )
    except (LlamaClientError, FileNotFoundError) as exc:
        _write_json(config.output_dir / f"{config.label}_error.json", {"error": str(exc)})
        return 1

    review_validation = validate_review(review_text)
    tool_diff_validation = validate_diff(
        tool_diff_text,
        require_tool=True,
        require_schema=False,
        required_first_header="diff --git a/tool.py b/tool.py",
        allowed_headers=["diff --git a/tool.py b/tool.py"],
    )
    schema_diff_validation = None
    if not config.skip_schema_diff:
        schema_diff_validation = validate_diff(
            schema_diff_text,
            require_tool=False,
            require_schema=True,
            required_first_header="diff --git a/input_schema.json b/input_schema.json",
            allowed_headers=[
                "diff --git a/input_schema.json b/input_schema.json",
                "diff --git a/usage_instructions.md b/usage_instructions.md",
            ],
        )

    validation_path = config.output_dir / "validation.json"
    validation_payload = _read_json_if_exists(validation_path)
    validation_payload[config.label] = {
        "review": {
            "ok": review_validation.ok,
            "errors": review_validation.errors,
            "warnings": review_validation.warnings,
        },
        "diff_tool": {
            "ok": tool_diff_validation.ok,
            "errors": tool_diff_validation.errors,
            "warnings": tool_diff_validation.warnings,
        },
    }
    if schema_diff_validation is not None:
        validation_payload[config.label]["diff_schema"] = {
            "ok": schema_diff_validation.ok,
            "errors": schema_diff_validation.errors,
            "warnings": schema_diff_validation.warnings,
        }
    _write_json(validation_path, validation_payload)

    comparison_path = config.output_dir / "comparison.json"
    comparison_payload = _read_json_if_exists(comparison_path)
    comparison_payload[config.label] = {
        "review": review_usage,
        "diff_tool": tool_diff_usage,
    }
    if schema_diff_usage is not None:
        comparison_payload[config.label]["diff_schema"] = schema_diff_usage
    _write_json(comparison_path, comparison_payload)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
