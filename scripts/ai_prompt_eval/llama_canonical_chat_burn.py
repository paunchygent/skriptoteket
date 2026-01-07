from __future__ import annotations

import argparse
import json
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class RequestSpec:
    name: str
    payload_bytes: bytes


@dataclass
class Stats:
    ok: int = 0
    err: int = 0
    latencies: list[float] = None
    last_errors: list[str] = None

    def __post_init__(self) -> None:
        if self.latencies is None:
            self.latencies = []
        if self.last_errors is None:
            self.last_errors = []


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _default_fixture_dir() -> Path:
    return (
        _repo_root()
        / "docs/reference/reports/artifacts/llama-canonical-chat-v3"
        / "llama-canonical-chat-v3-20260105T012947Z"
    )


def _parse_args() -> argparse.Namespace:
    default_fixture_dir = _default_fixture_dir()
    parser = argparse.ArgumentParser(
        description="10-minute llama.cpp burn test using canonical chat fixtures.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8082",
        help="llama.cpp server base URL.",
    )
    parser.add_argument(
        "--duration-seconds",
        type=int,
        default=600,
        help="Total test duration in seconds.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=8,
        help="Concurrent worker threads.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=180,
        help="HTTP timeout per request.",
    )
    parser.add_argument(
        "--fixture-dir",
        type=Path,
        default=default_fixture_dir,
        help="Directory containing review.request.json and diff.request.json.",
    )
    parser.add_argument(
        "--log-dir",
        type=Path,
        default=_repo_root() / ".artifacts/llama-canonical-chat-burn",
        help="Directory for run logs (created if missing).",
    )
    parser.add_argument(
        "--progress-interval",
        type=int,
        default=30,
        help="Seconds between progress updates.",
    )
    return parser.parse_args()


def _load_request(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Request payload is not an object: {path}")
    return payload


def _percentile(values: list[float], pct: float) -> float | None:
    if not values:
        return None
    values = sorted(values)
    idx = int(round((pct / 100.0) * (len(values) - 1)))
    return values[idx]


def _format_latency(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.2f}s"


def main() -> None:
    args = _parse_args()
    fixture_dir = args.fixture_dir
    review_path = fixture_dir / "review.request.json"
    diff_path = fixture_dir / "diff.request.json"
    if not review_path.exists() or not diff_path.exists():
        raise SystemExit(
            "Missing fixture files. Expected:\n"
            f"- {review_path}\n"
            f"- {diff_path}\n"
            "Either pass --fixture-dir or sync the artifacts folder."
        )

    review_payload = _load_request(review_path)
    diff_payload = _load_request(diff_path)
    review_bytes = json.dumps(review_payload, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )
    diff_bytes = json.dumps(diff_payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

    requests = [
        RequestSpec("review", review_bytes),
        RequestSpec("diff", diff_bytes),
    ]

    log_dir: Path = args.log_dir
    log_dir.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    log_path = log_dir / f"llama-canonical-chat-burn-{run_id}.log"

    stats = {
        "review": Stats(),
        "diff": Stats(),
        "total": Stats(),
    }
    lock = threading.Lock()
    end_time = time.time() + args.duration_seconds
    base_url = args.base_url.rstrip("/")
    endpoint = f"{base_url}/v1/chat/completions"

    def log(msg: str) -> None:
        print(msg, flush=True)
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(msg + "\n")

    log(f"llama-canonical-chat-burn start UTC={run_id}")
    log(f"endpoint={endpoint}")
    log(f"duration={args.duration_seconds}s workers={args.workers} timeout={args.timeout_seconds}s")
    log(f"fixture_dir={fixture_dir}")
    log("-")

    def worker(worker_id: int) -> None:
        idx = worker_id % len(requests)
        while time.time() < end_time:
            spec = requests[idx]
            idx = (idx + 1) % len(requests)
            t0 = time.time()
            ok = True
            error = None
            try:
                req = urllib.request.Request(
                    endpoint,
                    data=spec.payload_bytes,
                    headers={"Content-Type": "application/json"},
                )
                with urllib.request.urlopen(req, timeout=args.timeout_seconds) as resp:
                    resp.read()
                    if resp.status != 200:
                        ok = False
                        error = f"status {resp.status}"
            except urllib.error.HTTPError as exc:
                ok = False
                error = f"HTTPError {exc.code}"
            except Exception as exc:  # noqa: BLE001 - surface last error only
                ok = False
                error = f"{type(exc).__name__}: {exc}"
            elapsed = time.time() - t0
            with lock:
                stats["total"].latencies.append(elapsed)
                stats[spec.name].latencies.append(elapsed)
                if ok:
                    stats["total"].ok += 1
                    stats[spec.name].ok += 1
                else:
                    stats["total"].err += 1
                    stats[spec.name].err += 1
                    stats["total"].last_errors.append(error or "unknown error")
                    stats[spec.name].last_errors.append(error or "unknown error")
                    stats["total"].last_errors = stats["total"].last_errors[-5:]
                    stats[spec.name].last_errors = stats[spec.name].last_errors[-5:]

    def progress_loop() -> None:
        while time.time() < end_time:
            time.sleep(args.progress_interval)
            with lock:
                total = stats["total"]
                p50 = _percentile(total.latencies, 50)
                p95 = _percentile(total.latencies, 95)
                last_err = list(total.last_errors)
                ok = total.ok
                err = total.err
            elapsed = int(time.time() - (end_time - args.duration_seconds))
            log(
                f"t+{elapsed:4d}s ok={ok} err={err} p50={_format_latency(p50)} "
                f"p95={_format_latency(p95)} last_err={last_err}"
            )

    threads = [threading.Thread(target=worker, args=(i,), daemon=True) for i in range(args.workers)]
    progress = threading.Thread(target=progress_loop, daemon=True)
    progress.start()
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    with lock:
        total = stats["total"]
        total_p50 = _percentile(total.latencies, 50)
        total_p95 = _percentile(total.latencies, 95)
        total_p99 = _percentile(total.latencies, 99)

        review = stats["review"]
        diff = stats["diff"]
        review_p50 = _percentile(review.latencies, 50)
        review_p95 = _percentile(review.latencies, 95)
        diff_p50 = _percentile(diff.latencies, 50)
        diff_p95 = _percentile(diff.latencies, 95)

    log("-")
    log(
        "total"
        f" ok={total.ok} err={total.err}"
        f" p50={_format_latency(total_p50)}"
        f" p95={_format_latency(total_p95)}"
        f" p99={_format_latency(total_p99)}"
    )
    log(
        "review"
        f" ok={review.ok} err={review.err}"
        f" p50={_format_latency(review_p50)}"
        f" p95={_format_latency(review_p95)}"
    )
    log(
        "diff"
        f" ok={diff.ok} err={diff.err}"
        f" p50={_format_latency(diff_p50)}"
        f" p95={_format_latency(diff_p95)}"
    )
    log(f"log_path={log_path}")


if __name__ == "__main__":
    main()
