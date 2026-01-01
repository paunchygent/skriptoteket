from __future__ import annotations

import argparse
import json
import os
import statistics
import time
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

import httpx

from scripts.ai_prompt_eval.fixture_bank import (
    FIXTURES,
    EditSuggestionFixture,
    InlineCompletionFixture,
    PromptEvalFixture,
    PromptEvalOutcome,
)

_EVAL_REQUEST_HEADER = "X-Skriptoteket-Eval"


def _read_dotenv(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}

    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def _get_config_value(*, key: str, dotenv: dict[str, str]) -> str | None:
    return os.environ.get(key) or dotenv.get(key)


def _get_credentials(*, dotenv: dict[str, str]) -> tuple[str | None, str | None]:
    """Resolve eval harness credentials (bootstrap superuser preferred)."""

    email = os.environ.get("BOOTSTRAP_SUPERUSER_EMAIL") or dotenv.get("BOOTSTRAP_SUPERUSER_EMAIL")
    password = os.environ.get("BOOTSTRAP_SUPERUSER_PASSWORD") or dotenv.get(
        "BOOTSTRAP_SUPERUSER_PASSWORD"
    )
    if email is not None or password is not None:
        return email, password

    email = os.environ.get("PLAYWRIGHT_EMAIL") or dotenv.get("PLAYWRIGHT_EMAIL")
    password = os.environ.get("PLAYWRIGHT_PASSWORD") or dotenv.get("PLAYWRIGHT_PASSWORD")
    return email, password


@dataclass(frozen=True)
class HarnessConfig:
    base_url: str
    email: str
    password: str
    timeout_seconds: float
    artifacts_root: Path
    fixture_ids: tuple[str, ...]
    capabilities: frozenset[Literal["inline_completion", "edit_suggestion"]] | None


def _parse_args() -> HarnessConfig:
    pre_parser = argparse.ArgumentParser(add_help=False)
    pre_parser.add_argument(
        "--dotenv",
        default=os.environ.get("DOTENV_PATH") or ".env",
        help="Dotenv file for defaults (default: DOTENV_PATH env var or .env)",
    )
    pre_args, _ = pre_parser.parse_known_args()
    dotenv = _read_dotenv(Path(pre_args.dotenv))

    default_email, default_password = _get_credentials(dotenv=dotenv)

    parser = argparse.ArgumentParser(
        description="AI prompt evaluation harness (live backend + llama.cpp)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        parents=[pre_parser],
    )
    parser.add_argument(
        "--base-url",
        default=_get_config_value(key="BASE_URL", dotenv=dotenv) or "http://127.0.0.1:8000",
        help="Backend base URL (FastAPI server).",
    )
    parser.add_argument(
        "--email",
        default=default_email,
        help=(
            "Login email (default: BOOTSTRAP_SUPERUSER_EMAIL, fallback PLAYWRIGHT_EMAIL, from env/dotenv)."
        ),
    )
    parser.add_argument(
        "--password",
        default=default_password,
        help=(
            "Login password (default: BOOTSTRAP_SUPERUSER_PASSWORD, fallback PLAYWRIGHT_PASSWORD, from env/dotenv)."
        ),
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=float(os.environ.get("AI_PROMPT_EVAL_TIMEOUT_SECONDS", "120")),
        help="HTTP request timeout per fixture.",
    )
    parser.add_argument(
        "--artifacts-root",
        default=".artifacts/ai-prompt-eval",
        help="Root folder for run artifacts (metadata only).",
    )
    parser.add_argument(
        "--fixture-id",
        action="append",
        default=[],
        help="Run only a specific fixture id (repeatable).",
    )
    parser.add_argument(
        "--capability",
        action="append",
        default=[],
        choices=["inline_completion", "edit_suggestion"],
        help="Run only a capability (repeatable).",
    )

    args = parser.parse_args()

    if not args.email or not args.password:
        parser.error(
            "Missing credentials. Either:\n"
            "  1) Set BOOTSTRAP_SUPERUSER_EMAIL/BOOTSTRAP_SUPERUSER_PASSWORD in --dotenv (recommended)\n"
            "  2) Export them as environment variables\n"
            "  3) Pass --email and --password"
        )

    capabilities = frozenset(args.capability) if args.capability else None
    return HarnessConfig(
        base_url=args.base_url.rstrip("/"),
        email=args.email,
        password=args.password,
        timeout_seconds=args.timeout_seconds,
        artifacts_root=Path(args.artifacts_root),
        fixture_ids=tuple(args.fixture_id),
        capabilities=capabilities,
    )


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _run_id(now: datetime) -> str:
    return now.strftime("%Y%m%d-%H%M%S")


def _login(*, client: httpx.Client, email: str, password: str) -> str:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError("Login response is not an object")
    csrf_token = payload.get("csrf_token")
    if not isinstance(csrf_token, str) or not csrf_token:
        raise ValueError("Login response missing csrf_token")
    return csrf_token


def _coerce_int(value: str | None) -> int | None:
    if value is None:
        return None
    trimmed = value.strip()
    if not trimmed:
        return None
    try:
        return int(trimmed)
    except ValueError:
        return None


def _read_eval_meta_headers(headers: httpx.Headers) -> dict[str, object]:
    template_id = headers.get("X-Skriptoteket-Eval-Template-Id")
    outcome = headers.get("X-Skriptoteket-Eval-Outcome")

    meta: dict[str, object] = {
        "template_id": template_id.strip()
        if template_id is not None and template_id.strip()
        else None,
        "outcome": outcome.strip() if outcome is not None and outcome.strip() else None,
        "system_prompt_chars": _coerce_int(headers.get("X-Skriptoteket-Eval-System-Prompt-Chars")),
        "prefix_chars": _coerce_int(headers.get("X-Skriptoteket-Eval-Prefix-Chars")),
        "suffix_chars": _coerce_int(headers.get("X-Skriptoteket-Eval-Suffix-Chars")),
        "instruction_chars": _coerce_int(headers.get("X-Skriptoteket-Eval-Instruction-Chars")),
        "selection_chars": _coerce_int(headers.get("X-Skriptoteket-Eval-Selection-Chars")),
    }
    return meta


def _parse_error_meta(response: httpx.Response) -> dict[str, object]:
    try:
        payload = response.json()
    except ValueError:
        payload = None

    if not isinstance(payload, dict):
        return {}

    error = payload.get("error")
    correlation_id = payload.get("correlation_id")
    meta: dict[str, object] = {}

    if isinstance(error, dict):
        code = error.get("code")
        if isinstance(code, str):
            meta["error_code"] = code

    if isinstance(correlation_id, str):
        meta["correlation_id"] = correlation_id

    return meta


def _fixture_iter(
    *, fixture_ids: tuple[str, ...], capabilities: frozenset[str] | None
) -> tuple[PromptEvalFixture, ...]:
    fixtures = FIXTURES
    if fixture_ids:
        allowed = set(fixture_ids)
        fixtures = tuple(f for f in fixtures if f.fixture_id in allowed)
    if capabilities:
        fixtures = tuple(f for f in fixtures if f.capability in capabilities)
    return fixtures


def _read_outcome(
    *, meta: dict[str, object], response_chars: int, status_code: int
) -> PromptEvalOutcome:
    raw = meta.get("outcome")
    if isinstance(raw, str) and raw:
        if raw in {"ok", "empty", "truncated", "over_budget", "timeout", "error"}:
            return raw  # type: ignore[return-value]
        return "error"

    if status_code != 200:
        return "error"

    return "ok" if response_chars else "empty"


def _build_case_record(
    *,
    fixture: PromptEvalFixture,
    status_code: int | None,
    enabled: bool | None,
    response_chars: int | None,
    latency_ms: int | None,
    outcome: PromptEvalOutcome,
    template_id: str | None,
    system_prompt_chars: int | None,
    prefix_chars: int | None,
    suffix_chars: int | None,
    instruction_chars: int | None,
    selection_chars: int | None,
    allowed_outcomes: frozenset[PromptEvalOutcome] | None,
    error_meta: dict[str, object],
    error_kind: str | None,
) -> dict[str, object]:
    record: dict[str, object] = {
        "fixture_id": fixture.fixture_id,
        "capability": fixture.capability,
        "language": fixture.language,
        "http_status": status_code,
        "enabled": enabled,
        "latency_ms": latency_ms,
        "outcome": outcome,
        "template_id": template_id,
        "system_prompt_chars": system_prompt_chars,
        "prefix_chars": prefix_chars,
        "suffix_chars": suffix_chars,
        "instruction_chars": instruction_chars,
        "selection_chars": selection_chars,
        "response_chars": response_chars,
        "error_kind": error_kind,
    }

    unexpected = allowed_outcomes is not None and outcome not in allowed_outcomes
    record["unexpected_outcome"] = unexpected

    record.update(error_meta)
    return record


def _write_json(path: Path, payload: object) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _percentile(sorted_values: list[int], percentile: float) -> int:
    if not sorted_values:
        return 0
    index = int(round((len(sorted_values) - 1) * percentile))
    if index < 0:
        index = 0
    if index >= len(sorted_values):
        index = len(sorted_values) - 1
    return sorted_values[index]


def _summarize_latency(latencies_ms: list[int]) -> dict[str, float | int | None]:
    if not latencies_ms:
        return {
            "count": 0,
            "min_ms": None,
            "max_ms": None,
            "mean_ms": None,
            "p50_ms": None,
            "p95_ms": None,
        }

    ordered = sorted(latencies_ms)
    return {
        "count": len(latencies_ms),
        "min_ms": ordered[0],
        "max_ms": ordered[-1],
        "mean_ms": round(statistics.mean(latencies_ms), 2),
        "p50_ms": _percentile(ordered, 0.50),
        "p95_ms": _percentile(ordered, 0.95),
    }


def run() -> Path:
    config = _parse_args()
    started_at = _utc_now()

    selected_fixtures = _fixture_iter(
        fixture_ids=config.fixture_ids,
        capabilities=config.capabilities,
    )
    if not selected_fixtures:
        raise SystemExit("No fixtures selected.")

    run_dir = config.artifacts_root / _run_id(started_at)
    run_dir.mkdir(parents=True, exist_ok=True)

    client = httpx.Client(
        base_url=config.base_url,
        timeout=config.timeout_seconds,
    )
    try:
        csrf_token = _login(client=client, email=config.email, password=config.password)
        common_headers = {
            "X-CSRF-Token": csrf_token,
            _EVAL_REQUEST_HEADER: "1",
        }

        cases: list[dict[str, object]] = []
        latencies_all: list[int] = []
        latencies_ok: list[int] = []
        outcome_counts: Counter[str] = Counter()
        outcome_counts_by_capability: dict[str, Counter[str]] = {}
        http_status_counts: Counter[str] = Counter()
        templates_seen: set[str] = set()
        unexpected_count = 0

        for fixture in selected_fixtures:
            endpoint: str
            payload: dict[str, Any]
            allowed_outcomes = fixture.allowed_outcomes

            if isinstance(fixture, InlineCompletionFixture):
                endpoint = "/api/v1/editor/completions"
                payload = {"prefix": fixture.prefix, "suffix": fixture.suffix}
            elif isinstance(fixture, EditSuggestionFixture):
                endpoint = "/api/v1/editor/edits"
                payload = {
                    "prefix": fixture.prefix,
                    "selection": fixture.selection,
                    "suffix": fixture.suffix,
                    "instruction": fixture.instruction,
                }
            else:
                raise ValueError(f"Unknown fixture type: {type(fixture)!r}")

            status_code: int | None = None
            enabled: bool | None = None
            response_chars: int | None = None
            latency_ms: int | None = None
            error_kind: str | None = None
            error_meta: dict[str, object] = {}
            eval_meta: dict[str, object] = {}

            start = time.perf_counter()
            try:
                response = client.post(endpoint, json=payload, headers=common_headers)
                elapsed_ms = int((time.perf_counter() - start) * 1000)
                latency_ms = elapsed_ms
                latencies_all.append(elapsed_ms)
                status_code = response.status_code
                http_status_counts[str(status_code)] += 1

                if status_code != 200:
                    error_kind = "http_status"
                    error_meta = _parse_error_meta(response)
                else:
                    body = response.json()
                    if not isinstance(body, dict):
                        error_kind = "invalid_json"
                    else:
                        enabled_value = body.get("enabled")
                        if isinstance(enabled_value, bool):
                            enabled = enabled_value

                        output_value = body.get("completion")
                        if output_value is None:
                            output_value = body.get("suggestion")
                        if isinstance(output_value, str):
                            response_chars = len(output_value)

                eval_meta = _read_eval_meta_headers(response.headers)
            except httpx.TimeoutException:
                elapsed_ms = int((time.perf_counter() - start) * 1000)
                latency_ms = elapsed_ms
                latencies_all.append(elapsed_ms)
                error_kind = "timeout"
                outcome: PromptEvalOutcome = "timeout"
                case = _build_case_record(
                    fixture=fixture,
                    status_code=status_code,
                    enabled=enabled,
                    response_chars=response_chars,
                    latency_ms=latency_ms,
                    outcome=outcome,
                    template_id=None,
                    system_prompt_chars=None,
                    prefix_chars=None,
                    suffix_chars=None,
                    instruction_chars=None,
                    selection_chars=None,
                    allowed_outcomes=allowed_outcomes,
                    error_meta=error_meta,
                    error_kind=error_kind,
                )
                cases.append(case)
                outcome_counts[outcome] += 1
                outcome_counts_by_capability.setdefault(fixture.capability, Counter())[outcome] += 1
                if case.get("unexpected_outcome") is True:
                    unexpected_count += 1
                print(f"{fixture.fixture_id}: {fixture.capability} -> timeout ({elapsed_ms}ms)")
                continue
            except httpx.RequestError:
                elapsed_ms = int((time.perf_counter() - start) * 1000)
                latency_ms = elapsed_ms
                latencies_all.append(elapsed_ms)
                error_kind = "request_error"
                outcome = "error"
                case = _build_case_record(
                    fixture=fixture,
                    status_code=status_code,
                    enabled=enabled,
                    response_chars=response_chars,
                    latency_ms=latency_ms,
                    outcome=outcome,
                    template_id=None,
                    system_prompt_chars=None,
                    prefix_chars=None,
                    suffix_chars=None,
                    instruction_chars=None,
                    selection_chars=None,
                    allowed_outcomes=allowed_outcomes,
                    error_meta=error_meta,
                    error_kind=error_kind,
                )
                cases.append(case)
                outcome_counts[outcome] += 1
                outcome_counts_by_capability.setdefault(fixture.capability, Counter())[outcome] += 1
                if case.get("unexpected_outcome") is True:
                    unexpected_count += 1
                print(f"{fixture.fixture_id}: {fixture.capability} -> error ({elapsed_ms}ms)")
                continue

            outcome = _read_outcome(
                meta=eval_meta,
                response_chars=response_chars or 0,
                status_code=status_code or 0,
            )

            template_id = (
                eval_meta.get("template_id")
                if isinstance(eval_meta.get("template_id"), str)
                else None
            )
            if template_id:
                templates_seen.add(template_id)

            system_prompt_chars = (
                eval_meta.get("system_prompt_chars")
                if isinstance(eval_meta.get("system_prompt_chars"), int)
                else None
            )
            prefix_chars = (
                eval_meta.get("prefix_chars")
                if isinstance(eval_meta.get("prefix_chars"), int)
                else None
            )
            suffix_chars = (
                eval_meta.get("suffix_chars")
                if isinstance(eval_meta.get("suffix_chars"), int)
                else None
            )
            instruction_chars = (
                eval_meta.get("instruction_chars")
                if isinstance(eval_meta.get("instruction_chars"), int)
                else None
            )
            selection_chars = (
                eval_meta.get("selection_chars")
                if isinstance(eval_meta.get("selection_chars"), int)
                else None
            )

            if outcome == "ok" and latency_ms is not None:
                latencies_ok.append(latency_ms)

            case = _build_case_record(
                fixture=fixture,
                status_code=status_code,
                enabled=enabled,
                response_chars=response_chars,
                latency_ms=latency_ms,
                outcome=outcome,
                template_id=template_id,
                system_prompt_chars=system_prompt_chars,
                prefix_chars=prefix_chars,
                suffix_chars=suffix_chars,
                instruction_chars=instruction_chars,
                selection_chars=selection_chars,
                allowed_outcomes=allowed_outcomes,
                error_meta=error_meta,
                error_kind=error_kind,
            )
            cases.append(case)
            outcome_counts[outcome] += 1
            outcome_counts_by_capability.setdefault(fixture.capability, Counter())[outcome] += 1
            if case.get("unexpected_outcome") is True:
                unexpected_count += 1

            print(f"{fixture.fixture_id}: {fixture.capability} -> {outcome} ({latency_ms}ms)")

        finished_at = _utc_now()

        all_outcomes: tuple[PromptEvalOutcome, ...] = (
            "ok",
            "empty",
            "truncated",
            "over_budget",
            "timeout",
            "error",
        )

        summary: dict[str, object] = {
            "started_at": started_at.isoformat(),
            "finished_at": finished_at.isoformat(),
            "base_url": config.base_url,
            "fixture_count": len(selected_fixtures),
            "capabilities": sorted({f.capability for f in selected_fixtures}),
            "template_ids": sorted(templates_seen),
            "unexpected_outcomes": unexpected_count,
            "counts": {k: int(outcome_counts.get(k, 0)) for k in all_outcomes},
            "counts_by_capability": {
                cap: {k: int(counter.get(k, 0)) for k in all_outcomes}
                for cap, counter in sorted(outcome_counts_by_capability.items())
            },
            "http_status_counts": dict(sorted(http_status_counts.items())),
            "latency_all_ms": _summarize_latency(latencies_all),
            "latency_ok_ms": _summarize_latency(latencies_ok),
        }

        _write_json(run_dir / "summary.json", summary)
        cases_path = run_dir / "cases.jsonl"
        with cases_path.open("w", encoding="utf-8") as handle:
            for case in cases:
                handle.write(json.dumps(case, ensure_ascii=False, sort_keys=True) + "\n")

        print(f"Wrote artifacts: {run_dir}")
        return run_dir
    finally:
        client.close()


def main() -> None:
    run()


if __name__ == "__main__":
    main()
