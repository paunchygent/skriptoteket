from __future__ import annotations

import argparse
import sys
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

from scripts.ai_prompt_eval.llama_client import (  # noqa: E402
    LlamaClientError,
    send_chat_completion,
    wait_for_health,
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Send a single chat-completions request to a local llama.cpp server.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--prompt-path",
        required=True,
        help="Path to the prompt text file.",
    )
    parser.add_argument(
        "--output-path",
        help="Optional output file for the raw JSON response.",
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
        "--system-prompt-path",
        help="Optional system prompt file to prepend.",
    )
    parser.add_argument(
        "--wait-health",
        action="store_true",
        help="Wait for /health to return ok before sending the request.",
    )
    parser.add_argument(
        "--health-timeout-seconds",
        type=float,
        default=120.0,
        help="Max seconds to wait for /health when --wait-health is set.",
    )
    return parser.parse_args()


def _write_output(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def main() -> int:
    args = _parse_args()
    prompt_path = Path(args.prompt_path)
    if not prompt_path.exists():
        print(f"Prompt file not found: {prompt_path}", file=sys.stderr)
        return 2

    try:
        if args.wait_health:
            wait_for_health(
                base_url=args.base_url,
                timeout_seconds=args.health_timeout_seconds,
            )
        system_prompt = None
        if args.system_prompt_path:
            system_prompt = Path(args.system_prompt_path).read_text(encoding="utf-8")
        prompt = prompt_path.read_text(encoding="utf-8")
        data = send_chat_completion(
            prompt=prompt,
            base_url=args.base_url,
            model=args.model,
            temperature=args.temperature,
            max_tokens=args.max_tokens,
            timeout_seconds=args.timeout_seconds,
            system_prompt=system_prompt,
        )
    except LlamaClientError as exc:
        print(f"Request failed: {exc}", file=sys.stderr)
        return 1

    if args.output_path:
        _write_output(Path(args.output_path), data)
    else:
        sys.stdout.buffer.write(data)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
