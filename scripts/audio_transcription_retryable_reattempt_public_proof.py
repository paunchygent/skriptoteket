"""Audio Transcription retryable reattempt public browser proof.

Domain purpose:
    Prove the public authenticated Audio Transcription route receives
    Service API v2-owned retryable-failed idempotency reattempt behavior.

Relationships:
    Uses Skriptoteket Playwright/auth helpers and redacted Gateway evidence.
    Sir Convert sidecar/runtime precondition setup is an external operator
    step, not hidden in this browser proof.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from playwright.sync_api import sync_playwright

from scripts._audio_transcription_browser import (
    APP_PATH,
    open_transcript_lane,
    select_audio,
    start_transcript,
    wait_for_success,
)
from scripts._playwright_browser import launch_chromium
from scripts._playwright_config import get_config
from scripts._sir_convert_gateway_evidence import (
    GatewayCapture,
    assert_retryable_reattempt_evidence,
)
from scripts._transcript_parity_evidence import utc_now, write_json

PROOF_KIND = "audio_transcription_retryable_reattempt_public"
ARTIFACT_ROOT = Path(".artifacts/audio-transcription-retryable-reattempt-public-proof")
DEFAULT_AUDIO_FILE = Path(
    "/Users/olofs_mba/Documents/Repos/sir-convert-a-lot/"
    "build/verification/stt-sidecar-live-fixtures/source-media/"
    "swedish-monologue-one-speaker.m4a"
)


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audio Transcription retryable reattempt public browser proof"
    )
    parser.add_argument("--audio-file", default=str(DEFAULT_AUDIO_FILE))
    parser.add_argument("--base-url", default="https://skriptoteket.hule.education")
    parser.add_argument("--dotenv", default=".env.prod-smoke")
    parser.add_argument("--artifact-root", default=str(ARTIFACT_ROOT))
    parser.add_argument("--speaker-count", default=1, type=int)
    parser.add_argument("--timeout-seconds", default=900, type=int)
    parser.add_argument("--precondition-job-id", required=True)
    parser.add_argument("--precondition-idempotency-key", default=None)
    return parser.parse_args(argv)


def _run_dir(root: Path) -> Path:
    path = root / datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%SZ")
    path.mkdir(parents=True, exist_ok=False)
    return path


def run(argv: Sequence[str] | None = None) -> None:
    """Run the public browser reattempt proof and write retained evidence."""

    args = _parse_args(argv)
    config = get_config(["--dotenv", args.dotenv, "--base-url", args.base_url])
    audio_path = Path(args.audio_file).expanduser().resolve()
    if not audio_path.is_file():
        raise SystemExit(f"Audio file does not exist: {audio_path}")

    artifact_dir = _run_dir(Path(args.artifact_root).expanduser().resolve())
    capture = GatewayCapture(phase="replay")
    summary: dict[str, object] = {
        "proof_kind": PROOF_KIND,
        "status": "running",
        "started_at": utc_now(),
        "base_url": config.base_url,
        "app_path": APP_PATH,
        "precondition": {
            "source": "external_sir_convert_operator_step",
            "job_id": args.precondition_job_id,
            "idempotency_key_provided": args.precondition_idempotency_key is not None,
        },
        "audio_fixture": {
            "path": str(audio_path),
            "filename": audio_path.name,
            "size_bytes": audio_path.stat().st_size,
            "speaker_count": args.speaker_count,
        },
        "artifacts": {"run_dir": str(artifact_dir)},
    }

    with sync_playwright() as playwright:
        browser = launch_chromium(playwright)
        context = browser.new_context(
            accept_downloads=True, viewport={"width": 1440, "height": 900}
        )
        page = context.new_page()
        page.set_default_timeout(60_000)
        capture.attach(page)
        try:
            open_transcript_lane(
                page,
                base_url=config.base_url,
                email=config.email,
                password=config.password,
                artifact_dir=artifact_dir,
            )
            page.screenshot(
                path=str(artifact_dir / "authenticated-audio-transcription.png"), full_page=True
            )
            select_audio(page, audio_path=audio_path, speaker_count=args.speaker_count)
            start_transcript(page)
            wait_for_success(page, artifact_dir=artifact_dir, timeout_seconds=args.timeout_seconds)
            summary["proof"] = assert_retryable_reattempt_evidence(
                capture=capture,
                precondition_job_id=args.precondition_job_id,
                precondition_idempotency_key=args.precondition_idempotency_key,
            )
            summary["status"] = "passed"
        except Exception as exc:
            summary["status"] = "failed"
            summary["failure"] = {"type": type(exc).__name__, "message": str(exc)[:500]}
            try:
                page.screenshot(path=str(artifact_dir / "failure.png"), full_page=True)
            except Exception:
                pass
            raise
        finally:
            write_json(
                artifact_dir / "browser-create-requests.redacted.json", capture.request_records
            )
            write_json(
                artifact_dir / "browser-gateway-responses.redacted.json", capture.response_records
            )
            write_json(artifact_dir / "browser-console.redacted.json", capture.console_records)
            summary["completed_at"] = utc_now()
            write_json(artifact_dir / "proof-summary.json", summary)
            context.close()
            browser.close()

    print(json.dumps(summary, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    run()
