from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import httpx

from scripts._playwright_huleedu_auth import create_signed_huleedu_api_session
from scripts.ai_prompt_eval.cli import parse_args, select_fixtures
from scripts.ai_prompt_eval.fixture_execution import CaseResult, execute_fixture
from scripts.ai_prompt_eval.reporting import write_run_artifacts

_EVAL_REQUEST_HEADER = "X-Skriptoteket-Eval"


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _run_id(now: datetime) -> str:
    return now.strftime("%Y%m%d-%H%M%S")


def run() -> Path:
    config = parse_args()
    started_at = _utc_now()

    selected_fixtures = select_fixtures(
        fixture_ids=config.fixture_ids,
        capabilities=config.capabilities,
    )
    if not selected_fixtures:
        raise SystemExit("No fixtures selected.")

    run_dir = config.artifacts_root / _run_id(started_at)
    run_dir.mkdir(parents=True, exist_ok=True)

    auth = create_signed_huleedu_api_session(
        email=config.email,
        display_name="AI Prompt Eval Teacher",
        role="superuser",
        jti=f"ai-prompt-eval-{_run_id(started_at)}",
    )
    headers = {**auth.signed_headers, _EVAL_REQUEST_HEADER: "1"}

    cases: list[CaseResult] = []
    with httpx.Client(base_url=config.base_url, timeout=config.timeout_seconds) as client:
        for fixture in selected_fixtures:
            case = execute_fixture(client=client, fixture=fixture, headers=headers)
            cases.append(case)
            print(
                f"{fixture.fixture_id}: {fixture.capability} -> {case.outcome} ({case.latency_ms}ms)"
            )

    write_run_artifacts(
        run_dir=run_dir,
        cases=cases,
        base_url=config.base_url,
        started_at=started_at,
        finished_at=_utc_now(),
    )
    print(f"Wrote artifacts: {run_dir}")
    return run_dir


def main() -> None:
    run()


if __name__ == "__main__":
    main()
