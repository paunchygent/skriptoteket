"""Mock-mode load proof for 1,000 concurrent AI calls through the door client.

Purpose:
    Prove TASK-SKRIPT-41-01-04 (ST-SKRIPT-41-01 B7): Skriptoteket's door client,
    composed by the real DI container with the process and pool settings in the
    environment, carries 1,000 concurrent AI calls to HuleEdu's LLM provider
    door in mock mode. Every call completes or ends as the try-again answer
    (``AiDoorBusy``); no call reaches OpenAI.

    Web processes each send their share of one-call AI actions at once, the way
    concurrent editor requests do; one worker process runs several jobs whose
    calls share each job's fan-out bound. The parent samples the door's own
    ``llm_provider_openai_door_active_calls`` gauge, so the proof counts calls
    the door is actually serving, not configured ones. "No paid call" comes from
    the door: every completed reply carries the mock's ``resp_mock_`` response
    id, the gauge's ``mock`` child carries the load and its ``openai`` child
    stays 0 for the whole run.

Relationships:
    Runs inside a Skriptoteket container (or any checkout) that reaches the
    door; ``HULEEDU_LLM_PROVIDER_BASE_URL`` and ``HULEEDU_INTERNAL_API_KEY``
    point at the mock door. Writes ``summary.json`` and ``door-samples.jsonl``
    into ``--evidence-dir``.

Usage:
    python -m scripts.llm_door_load_proof --evidence-dir <dir> \
        --web-processes 4 --web-calls 840 --worker-jobs 8 --calls-per-job 20
"""

from __future__ import annotations

import argparse
import asyncio
import json
import multiprocessing
import re
import sys
import time
from collections import Counter
from collections.abc import Sequence
from dataclasses import asdict, dataclass, field
from pathlib import Path
from uuid import uuid4

import httpx

from skriptoteket.config import Settings
from skriptoteket.di import create_container
from skriptoteket.domain.llm_door import (
    AiDailyLimitReached,
    AiDoorBusy,
    AiDoorCaller,
    tooling_caller,
)
from skriptoteket.protocols.llm_door import (
    DoorOperation,
    DoorRequestFailed,
    DoorTimeout,
    LlmDoorClientProtocol,
)

_ACTIVE_GAUGE = re.compile(
    r'^llm_provider_openai_door_active_calls\{provider="(?P<provider>[a-z]+)"\}\s+(?P<value>\S+)$',
    re.MULTILINE,
)
_PROMPT = "Svara med ett ord: vilken färg har himlen en klar dag?"


@dataclass
class ProcessResult:
    role: str
    calls: int
    outcomes: dict[str, int] = field(default_factory=dict)
    statuses: dict[str, int] = field(default_factory=dict)
    seconds_p50: float = 0.0
    seconds_max: float = 0.0
    error_samples: list[str] = field(default_factory=list)


def _payload() -> dict[str, object]:
    return {
        "model": "gpt-6-luna",
        "input": _PROMPT,
        "max_output_tokens": 64,
    }


async def _one_call(
    door: LlmDoorClientProtocol, caller: AiDoorCaller, timeout_seconds: float
) -> tuple[str, str, float]:
    started = time.monotonic()
    try:
        reply = await door.send(
            operation=DoorOperation.RESPONSES,
            payload=_payload(),
            caller=caller,
            timeout_seconds=timeout_seconds,
        )
    except AiDoorBusy:
        return "try_again", "busy", time.monotonic() - started
    except AiDailyLimitReached as exc:
        return "daily_limit", exc.limit.value, time.monotonic() - started
    except DoorTimeout:
        return "door_timeout", "timeout", time.monotonic() - started
    except DoorRequestFailed as exc:
        return "request_failed", type(exc.__cause__).__name__, time.monotonic() - started
    if not reply.is_success:
        return "other_reply", str(reply.status_code), time.monotonic() - started
    outcome = "completed" if _is_mock_reply(reply.body) else "unfingerprinted_reply"
    return outcome, str(reply.status_code), time.monotonic() - started


def _is_mock_reply(body: bytes) -> bool:
    try:
        decoded: object = json.loads(body)
    except ValueError:
        return False
    return isinstance(decoded, dict) and str(decoded.get("id", "")).startswith("resp_mock_")


async def _run_process(
    role: str, actions: int, calls_per_action: int, start_at: float, timeout: float
) -> ProcessResult:
    settings = Settings()
    container = create_container(settings)
    try:
        door = await container.get(LlmDoorClientProtocol)
        callers = [
            tooling_caller(user_id=uuid4(), paid_overage_approved=False) for _ in range(actions)
        ]
        await asyncio.sleep(max(0.0, start_at - time.time()))
        results = await asyncio.gather(
            *(
                _one_call(door, caller, timeout)
                for caller in callers
                for _ in range(calls_per_action)
            )
        )
    finally:
        await container.close()
    durations = sorted(seconds for _, _, seconds in results)
    errors = [
        f"{outcome}:{detail}"
        for outcome, detail, _ in results
        if outcome not in {"completed", "try_again"}
    ]
    return ProcessResult(
        role=role,
        calls=len(results),
        outcomes=dict(Counter(outcome for outcome, _, _ in results)),
        statuses=dict(Counter(detail for _, detail, _ in results)),
        seconds_p50=round(durations[len(durations) // 2], 3),
        seconds_max=round(durations[-1], 3),
        error_samples=errors[:10],
    )


def _process_entry(
    role: str, actions: int, calls_per_action: int, start_at: float, timeout: float, out: str
) -> None:
    result = asyncio.run(_run_process(role, actions, calls_per_action, start_at, timeout))
    Path(out).write_text(json.dumps(asdict(result)), encoding="utf-8")


def _active_calls(metrics_text: str) -> dict[str, float]:
    return {m["provider"]: float(m["value"]) for m in _ACTIVE_GAUGE.finditer(metrics_text)}


async def _sample_door(
    client: httpx.AsyncClient, base_url: str, stop: asyncio.Event, samples_path: Path
) -> dict[str, float]:
    peaks: dict[str, float] = {}
    with samples_path.open("w", encoding="utf-8") as samples:
        while not stop.is_set():
            try:
                response = await client.get(f"{base_url}/metrics", timeout=2.0)
                active = _active_calls(response.text)
            except httpx.HTTPError as exc:
                active = {}
                samples.write(json.dumps({"t": time.time(), "error": type(exc).__name__}) + "\n")
            else:
                samples.write(json.dumps({"t": time.time(), "active": active}) + "\n")
                for provider, value in active.items():
                    peaks[provider] = max(peaks.get(provider, 0.0), value)
            await asyncio.sleep(0.1)
    return peaks


def _spread(total: int, parts: int) -> list[int]:
    return [total // parts + (1 if index < total % parts else 0) for index in range(parts)]


async def _main(args: argparse.Namespace) -> int:
    settings = Settings()
    base_url = settings.HULEEDU_LLM_PROVIDER_BASE_URL.rstrip("/")
    evidence = Path(args.evidence_dir)
    evidence.mkdir(parents=True, exist_ok=True)
    async with httpx.AsyncClient() as client:
        baseline = _active_calls((await client.get(f"{base_url}/metrics", timeout=5.0)).text)
        if "mock" not in baseline or "openai" not in baseline:
            print(f"Door exposes no active-call gauge: {baseline}", file=sys.stderr)
            return 2
        start_at = time.time() + args.start_delay_seconds
        plan: list[tuple[str, int, int]] = [
            (f"web-{index}", share, 1)
            for index, share in enumerate(_spread(args.web_calls, args.web_processes))
        ]
        if args.worker_jobs:
            plan.append(("worker", args.worker_jobs, args.calls_per_job))
        context = multiprocessing.get_context("spawn")
        processes = []
        for role, actions, calls_per_action in plan:
            out = evidence / f"process-{role}.json"
            process = context.Process(
                target=_process_entry,
                args=(
                    role,
                    actions,
                    calls_per_action,
                    start_at,
                    args.call_timeout_seconds,
                    str(out),
                ),
            )
            process.start()
            processes.append((process, out))
        stop = asyncio.Event()
        sampler = asyncio.create_task(
            _sample_door(client, base_url, stop, evidence / "door-samples.jsonl")
        )
        started = time.monotonic()
        while any(process.is_alive() for process, _ in processes):
            await asyncio.sleep(0.2)
        wall_seconds = time.monotonic() - started
        stop.set()
        peaks = await sampler

    results = [json.loads(out.read_text(encoding="utf-8")) for _, out in processes if out.exists()]
    outcomes: Counter[str] = Counter()
    for result in results:
        outcomes.update(result["outcomes"])
    planned = sum(actions * calls for _, actions, calls in plan)
    total = sum(outcomes.values())
    unexpected = total - outcomes["completed"] - outcomes["try_again"]
    paid = peaks.get("openai", 0.0)
    passed = (
        len(results) == len(plan)
        and total == planned
        and unexpected == 0
        and paid == 0.0
        and peaks.get("mock", 0.0) > 0.0
    )
    summary = {
        "passed": passed,
        "planned_calls": planned,
        "finished_calls": total,
        "outcomes": dict(outcomes),
        "unexpected_outcomes": unexpected,
        "door_peak_active_calls": peaks,
        "paid_calls_seen_at_door": paid,
        "wall_seconds": round(wall_seconds, 2),
        "call_timeout_seconds": args.call_timeout_seconds,
        "settings": {
            "LLM_DOOR_MAX_IN_FLIGHT": settings.LLM_DOOR_MAX_IN_FLIGHT,
            "LLM_DOOR_MAX_CONNECTIONS": settings.LLM_DOOR_MAX_CONNECTIONS,
            "LLM_JOB_MAX_IN_FLIGHT": settings.LLM_JOB_MAX_IN_FLIGHT,
            "LLM_DOOR_CAPACITY_RETRIES": settings.LLM_DOOR_CAPACITY_RETRIES,
            "LLM_DOOR_SLOT_WAIT_SECONDS": settings.LLM_DOOR_SLOT_WAIT_SECONDS,
        },
        "plan": [{"role": role, "actions": a, "calls_per_action": c} for role, a, c in plan],
        "processes": results,
    }
    (evidence / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(
        json.dumps(
            {
                k: summary[k]
                for k in ("passed", "outcomes", "door_peak_active_calls", "wall_seconds")
            }
        )
    )
    return 0 if passed else 1


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0] if __doc__ else None)
    parser.add_argument("--evidence-dir", required=True)
    parser.add_argument("--web-processes", type=int, default=4)
    parser.add_argument("--web-calls", type=int, default=840)
    parser.add_argument("--worker-jobs", type=int, default=8)
    parser.add_argument("--calls-per-job", type=int, default=20)
    parser.add_argument("--start-delay-seconds", type=float, default=5.0)
    # Above the mock's longest recorded latency (56.5 s), like the exam providers.
    parser.add_argument("--call-timeout-seconds", type=float, default=120.0)
    return asyncio.run(_main(parser.parse_args(argv)))


if __name__ == "__main__":
    raise SystemExit(main())
