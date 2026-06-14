"""PR-0349 live transcript parity proof.

Domain purpose:
    Prove the authenticated transcript lane across progress, cancel, save,
    overlays, formatter exports, downloads, and Mina filer save.

Relationships:
    Uses HuleEdu browser-session helpers and writes sanitized PR-0349 evidence
    under `.artifacts/playwright-pr-0349-transcript-parity-live/`.
"""

from __future__ import annotations

import argparse
import json
import shutil
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path

from playwright.sync_api import Page, expect, sync_playwright

from scripts._playwright_auth import login_via_auth_entry
from scripts._playwright_browser import launch_chromium
from scripts._playwright_config import get_config
from scripts._transcript_parity_cancel import classify_cancel_path
from scripts._transcript_parity_evidence import (
    CapturedResponse,
    capture_transcript_response,
    collect_network,
    finalize_proof_summary,
    json_payload,
    safe_path,
    scrub_payload,
    speaker_labels_from_transcript,
    transcript_summary,
    utc_now,
    write_json,
)
from scripts._transcript_parity_evidence import (
    captured_artifact_summary as captured_artifact_summary,
)

APP_PATH = "/apps/documents.conversion_hub"
ARTIFACT_ROOT = Path(".artifacts/playwright-pr-0349-transcript-parity-live")
DEFAULT_AUDIO_FILE = Path(
    "/Users/olofs_mba/Documents/Repos/sir-convert-a-lot/"
    "build/verification/stt-sidecar-live-fixtures/source-media/"
    "english-dialogue-two-speakers.mp3"
)
ARTIFACT_KEYS = ("transcript_txt", "transcript_md", "transcript_vtt", "transcript_srt")
OVERLAY_LABELS = ("PR0349 Speaker A", "PR0349 Speaker B")
SCREENSHOTS = (
    "cancel-accepted.png",
    "progress.png",
    "transcript-succeeded.png",
    "formatter-artifacts.png",
    "complete.png",
)


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="PR-0349 transcript parity live proof")
    parser.add_argument("--audio-file", default=str(DEFAULT_AUDIO_FILE))
    parser.add_argument("--base-url", default="http://127.0.0.1:5173")
    parser.add_argument("--dotenv", default=".env")
    parser.add_argument("--artifact-root", default=str(ARTIFACT_ROOT))
    parser.add_argument("--speaker-count", default=2, type=int)
    parser.add_argument("--timeout-seconds", default=1_200, type=int)
    return parser.parse_args(argv)


def _run_dir(root: Path) -> Path:
    path = root / datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%SZ")
    path.mkdir(parents=True, exist_ok=False)
    (path / "downloads").mkdir()
    return path


def _copy_audio_for_submission(*, audio_path: Path, artifact_dir: Path, purpose: str) -> Path:
    target = (
        artifact_dir
        / f"{purpose}-{datetime.now(tz=UTC).strftime('%Y%m%dT%H%M%S%fZ')}-{audio_path.name}"
    )
    shutil.copy2(audio_path, target)
    return target


def _open_transcript_lane(
    page: Page, *, base_url: str, email: str, password: str, artifact_dir: Path
) -> None:
    login_via_auth_entry(
        page,
        base_url=base_url,
        email=email,
        password=password,
        next_path=APP_PATH,
        success_heading_pattern=r"Konvertera prov|Transkribera samtal|Välj inspelning|Valj inspelning",
        failure_artifacts_dir=artifact_dir,
        success_timeout_ms=45_000,
    )
    page.locator('[data-test="conversion-hub-mode-transcript"]').click()
    expect(page.locator('[data-test="transcript-workflow-rail-shell"]')).to_be_visible()


def _select_audio(page: Page, *, audio_path: Path, speaker_count: int) -> None:
    page.locator('[data-test="transcript-source-file-input"]').set_input_files(str(audio_path))
    page.locator('[data-test="transcript-speaker-mode-known"]').click()
    speaker_count_input = page.locator('[data-test="transcript-speaker-count"]')
    speaker_count_input.fill(str(speaker_count))


def _start_transcript(page: Page) -> None:
    expect(page.locator('[data-test="transcript-start"]')).to_be_enabled(timeout=30_000)
    page.locator('[data-test="transcript-start"]').click()
    expect(page.locator('[data-test="transcript-running-surface"]')).to_be_visible(timeout=45_000)


def _first_non_empty_text(page: Page, selector: str) -> str | None:
    locator = page.locator(selector)
    if locator.count() == 0 or not locator.first.is_visible():
        return None
    text = locator.first.inner_text(timeout=2_000).strip()
    return text or None


def _capture_progress_snapshot(
    page: Page, *, artifact_dir: Path, timeout_seconds: int
) -> dict[str, object]:
    deadline = datetime.now(tz=UTC).timestamp() + timeout_seconds
    while datetime.now(tz=UTC).timestamp() < deadline:
        values = {
            "phase_visible": _first_non_empty_text(page, '[data-test="transcript-progress-phase"]')
            is not None,
            "percent_visible": _first_non_empty_text(
                page, '[data-test="transcript-progress-percent"]'
            )
            is not None,
            "duration_visible": _first_non_empty_text(
                page, '[data-test="transcript-progress-duration"]'
            )
            is not None,
            "chunks_visible": _first_non_empty_text(
                page, '[data-test="transcript-progress-chunks"]'
            )
            is not None,
            "heartbeat_visible": _first_non_empty_text(
                page, '[data-test="transcript-progress-heartbeat"]'
            )
            is not None,
        }
        if values["phase_visible"] and any(values[key] for key in values if key != "phase_visible"):
            page.screenshot(path=str(artifact_dir / "progress.png"), full_page=True)
            return values
        if page.locator('[data-test="transcript-result-surface"]').count() > 0:
            break
        page.wait_for_timeout(1_000)
    page.screenshot(path=str(artifact_dir / "progress-timeout.png"), full_page=True)
    raise AssertionError("Progress fields did not render before terminal state.")


def _exercise_cancel(
    page: Page,
    *,
    audio_path: Path,
    speaker_count: int,
    artifact_dir: Path,
    captured: list[CapturedResponse],
) -> dict[str, object]:
    _select_audio(page, audio_path=audio_path, speaker_count=speaker_count)
    _start_transcript(page)
    expect(page.locator('[data-test="transcript-cancel"]')).to_be_enabled(timeout=30_000)
    cancel_capture_start = len(captured)
    page.locator('[data-test="transcript-cancel"]').click()
    expect(page.locator('[data-test="transcript-canceled-surface"]')).to_be_visible(timeout=60_000)
    page.screenshot(path=str(artifact_dir / "cancel-accepted.png"), full_page=True)
    if page.locator('[data-test="transcript-save-button"]').count() > 0:
        raise AssertionError("Canceled job exposed a transcript save action.")
    cancel_evidence = classify_cancel_path(collect_network(captured[cancel_capture_start:]))
    page.locator('[data-test="transcript-reset"]').click()
    return {
        **cancel_evidence,
        "canceled_surface_visible": True,
        "invalid_save_action_absent": True,
    }


def _wait_for_success(page: Page, *, artifact_dir: Path, timeout_seconds: int) -> None:
    deadline = datetime.now(tz=UTC).timestamp() + timeout_seconds
    while datetime.now(tz=UTC).timestamp() < deadline:
        if page.locator('[data-test="transcript-failed-surface"]').count() > 0:
            page.screenshot(path=str(artifact_dir / "transcript-failed.png"), full_page=True)
            raise AssertionError("Transcript job failed in UI.")
        if page.locator('[data-test="transcript-result-surface"]').count() > 0:
            page.screenshot(path=str(artifact_dir / "transcript-succeeded.png"), full_page=True)
            return
        page.wait_for_timeout(2_000)
    page.screenshot(path=str(artifact_dir / "transcript-timeout.png"), full_page=True)
    raise AssertionError("Timed out waiting for transcript success.")


def _save_transcript(page: Page) -> dict[str, object]:
    expect(page.locator('[data-test="transcript-save-button"]')).to_be_enabled(timeout=60_000)
    with page.expect_response(
        lambda r: "/transcripts/jobs/" in r.url and r.request.method == "POST",
        timeout=60_000,
    ) as info:
        page.locator('[data-test="transcript-save-button"]').click()
    response = info.value
    if response.status >= 400:
        raise AssertionError(f"Transcript save failed with HTTP {response.status}.")
    expect(page.locator('[data-test="transcript-speaker-overlays"]')).to_be_visible(timeout=30_000)
    payload = json_payload(response)
    if not isinstance(payload, dict) or not isinstance(payload.get("transcript_id"), str):
        raise AssertionError("Transcript save response did not include a transcript id.")
    return {"transcript_id": payload["transcript_id"], "status": response.status}


def _save_speaker_overlays(page: Page, labels: list[str]) -> dict[str, object]:
    if len(labels) < 2:
        raise AssertionError("PR-0349 proof requires at least two canonical speaker labels.")
    for label, display_name in zip(labels[:2], OVERLAY_LABELS, strict=True):
        page.locator(f'[data-test="transcript-speaker-name-{label}"]').fill(display_name)
    with page.expect_response(
        lambda r: r.url.endswith("/speaker-overlays") and r.request.method == "PUT",
        timeout=60_000,
    ) as info:
        page.locator('[data-test="transcript-speaker-overlays-save"]').click()
    response = info.value
    if response.status >= 400:
        raise AssertionError(f"Speaker overlay save failed with HTTP {response.status}.")
    expect(page.locator('[data-test="transcript-formatter-replay-button"]')).to_be_enabled(
        timeout=30_000
    )
    return {"status": response.status, "overlay_count": 2}


def _string_keyed_dicts(values: object) -> list[dict[str, object]]:
    if not isinstance(values, list):
        return []
    items: list[dict[str, object]] = []
    for value in values:
        if not isinstance(value, dict):
            continue
        normalized: dict[str, object] = {}
        for key, nested in value.items():
            if not isinstance(key, str):
                normalized = {}
                break
            normalized[key] = nested
        if normalized:
            items.append(normalized)
    return items


def _request_formatter_export(page: Page) -> list[dict[str, object]]:
    with page.expect_response(
        lambda r: r.url.endswith("/formatter-exports") and r.request.method == "POST",
        timeout=180_000,
    ) as info:
        page.locator('[data-test="transcript-formatter-replay-button"]').click()
    response = info.value
    if response.status >= 400:
        raise AssertionError(f"Formatter export failed with HTTP {response.status}.")
    payload = json_payload(response)
    status = payload.get("status") if isinstance(payload, dict) else None
    if status != "succeeded":
        raise AssertionError(f"Formatter export did not succeed: status={status!r}.")
    artifacts_payload = payload.get("artifacts") if isinstance(payload, dict) else None
    artifacts = _string_keyed_dicts(artifacts_payload)
    if len(artifacts) != len(ARTIFACT_KEYS):
        raise AssertionError("Formatter export did not return all requested artifacts.")
    for key in ARTIFACT_KEYS:
        expect(page.locator(f'[data-test="transcript-download-artifact-{key}"]')).to_be_visible(
            timeout=30_000
        )
    return artifacts


def _verify_download_content(path: Path, *, forbidden_labels: list[str]) -> dict[str, object]:
    text = path.read_text(encoding="utf-8", errors="replace")
    missing = [label for label in OVERLAY_LABELS if label not in text]
    forbidden = [label for label in forbidden_labels if label.lower() in text.lower()]
    if missing or forbidden:
        raise AssertionError(
            f"Overlay artifact check failed for {path.name}: missing={missing}, forbidden={forbidden}"
        )
    return {
        "path": str(path),
        "size_bytes": path.stat().st_size,
        "overlay_labels_present": True,
        "fallback_labels_absent": True,
    }


def _download_artifacts(
    page: Page,
    *,
    artifacts: Sequence[Mapping[str, object]],
    artifact_dir: Path,
    forbidden_labels: list[str],
) -> dict[str, object]:
    downloaded: dict[str, object] = {}
    by_key: dict[str, Mapping[str, object]] = {}
    for artifact in artifacts:
        artifact_key = artifact.get("artifact_key")
        if isinstance(artifact_key, str):
            by_key[artifact_key] = artifact
    for key in ARTIFACT_KEYS:
        artifact = by_key.get(key)
        if artifact is None:
            raise AssertionError(f"Missing formatter export artifact {key}.")
        button = page.locator(f'[data-test="transcript-download-artifact-{key}"]')
        expect(button).to_be_enabled(timeout=30_000)
        with page.expect_response(
            lambda r, expected=key: (
                f"/formatter-artifacts/{expected}/download" in r.url and r.request.method == "GET"
            ),
            timeout=60_000,
        ) as response_info:
            with page.expect_download(timeout=60_000) as download_info:
                button.click()
        response = response_info.value
        if response.status >= 400:
            raise AssertionError(f"Download for {key} failed with HTTP {response.status}.")
        download = download_info.value
        artifact_filename = artifact.get("filename")
        fallback_filename = (
            artifact_filename if isinstance(artifact_filename, str) else f"{key}.txt"
        )
        filename = download.suggested_filename or fallback_filename
        output_path = artifact_dir / "downloads" / filename
        download.save_as(str(output_path))
        downloaded[key] = {
            **_verify_download_content(output_path, forbidden_labels=forbidden_labels),
            "status": response.status,
            "content_type": response.headers.get("content-type"),
        }
    return downloaded


def _save_representative_artifact(page: Page, key: str = "transcript_txt") -> dict[str, object]:
    button = page.locator(f'[data-test="transcript-save-artifact-{key}"]')
    expect(button).to_be_enabled(timeout=30_000)
    with page.expect_response(
        lambda r: f"/formatter-artifacts/{key}/save" in r.url and r.request.method == "POST",
        timeout=60_000,
    ) as info:
        button.click()
    response = info.value
    if response.status >= 400:
        raise AssertionError(f"Mina filer save for {key} failed with HTTP {response.status}.")
    payload = json_payload(response)
    return {"status": response.status, "saved": scrub_payload(safe_path(response.url), payload)}


def run(argv: Sequence[str] | None = None) -> None:
    args = _parse_args(argv)
    config = get_config(["--dotenv", args.dotenv, "--base-url", args.base_url])
    audio_path = Path(args.audio_file).expanduser().resolve()
    if not audio_path.is_file():
        raise SystemExit(f"Audio file does not exist: {audio_path}")

    artifact_dir = _run_dir(Path(args.artifact_root).resolve())
    cancel_audio_path = _copy_audio_for_submission(
        audio_path=audio_path,
        artifact_dir=artifact_dir,
        purpose="cancel",
    )
    main_audio_path = _copy_audio_for_submission(
        audio_path=audio_path,
        artifact_dir=artifact_dir,
        purpose="main",
    )
    captured: list[CapturedResponse] = []
    console_records: list[dict[str, str]] = []
    summary: dict[str, object] = {
        "proof_kind": "pr_0349_transcript_parity_live",
        "observed_at": utc_now(),
        "base_url": config.base_url,
        "app_path": APP_PATH,
        "source_media": {
            "fixture": "sir-convert-stt-english-two-speaker",
            "size_bytes": audio_path.stat().st_size,
            "proof_uploads": {
                "cancel_filename": cancel_audio_path.name,
                "main_filename": main_audio_path.name,
            },
        },
        "artifacts": {"artifact_dir": str(artifact_dir)},
    }

    with sync_playwright() as playwright:
        browser = launch_chromium(playwright)
        context = browser.new_context(accept_downloads=True, ignore_https_errors=False)
        page = context.new_page()
        page.set_default_timeout(30_000)
        page.on("response", lambda response: capture_transcript_response(captured, response))
        page.on(
            "console",
            lambda message: console_records.append(
                {"type": message.type, "text": message.text[:300]}
            ),
        )
        page.on(
            "pageerror",
            lambda error: console_records.append({"type": "pageerror", "text": str(error)[:300]}),
        )
        try:
            _open_transcript_lane(
                page,
                base_url=config.base_url,
                email=config.email,
                password=config.password,
                artifact_dir=artifact_dir,
            )
            summary["cancel"] = _exercise_cancel(
                page,
                audio_path=cancel_audio_path,
                speaker_count=args.speaker_count,
                artifact_dir=artifact_dir,
                captured=captured,
            )
            _select_audio(page, audio_path=main_audio_path, speaker_count=args.speaker_count)
            _start_transcript(page)
            summary["progress_ui"] = _capture_progress_snapshot(
                page,
                artifact_dir=artifact_dir,
                timeout_seconds=min(args.timeout_seconds, 240),
            )
            _wait_for_success(page, artifact_dir=artifact_dir, timeout_seconds=args.timeout_seconds)
            summary["save_transcript"] = _save_transcript(page)

            transcript_payload = None
            for item in captured:
                if safe_path(item.response.url).endswith("/artifacts/transcript_json"):
                    transcript_payload = json_payload(item.response)
            speaker_labels = speaker_labels_from_transcript(transcript_payload)
            summary["transcript_json"] = transcript_summary(transcript_payload)
            summary["speaker_overlays"] = _save_speaker_overlays(page, speaker_labels)
            formatter_artifacts = _request_formatter_export(page)
            page.screenshot(path=str(artifact_dir / "formatter-artifacts.png"), full_page=True)
            summary["formatter_export"] = {
                "artifact_keys": sorted(
                    str(artifact.get("artifact_key")) for artifact in formatter_artifacts
                ),
                "artifact_count": len(formatter_artifacts),
            }
            summary["downloads"] = _download_artifacts(
                page,
                artifacts=formatter_artifacts,
                artifact_dir=artifact_dir,
                forbidden_labels=speaker_labels,
            )
            summary["mina_filer_save"] = _save_representative_artifact(page)
            page.screenshot(path=str(artifact_dir / "complete.png"), full_page=True)
            summary["status"] = "passed"
        except Exception as exc:
            summary["status"] = "failed"
            summary["failure"] = {
                "type": exc.__class__.__name__,
                "message": str(exc)[:500],
            }
            try:
                page.screenshot(path=str(artifact_dir / "failure.png"), full_page=True)
            except Exception:
                pass
            raise
        finally:
            network_records = collect_network(captured)
            write_json(artifact_dir / "network.bounded.json", network_records)
            write_json(artifact_dir / "browser-console.bounded.json", console_records)
            finalize_proof_summary(
                summary,
                artifact_dir=artifact_dir,
                network_records=network_records,
            )
            write_json(artifact_dir / "proof-summary.json", summary)
            context.close()
            browser.close()

    print(json.dumps(summary, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    run()
