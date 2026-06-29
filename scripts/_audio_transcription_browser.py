"""Audio Transcription browser route helpers.

Domain purpose:
    Drive the authenticated Audio Transcription app route through stable
    route-owned selectors for retained browser proofs.

Relationships:
    Uses the shared HuleEdu auth-entry helper and is consumed by transcript
    parity plus retryable-reattempt proof scripts.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from playwright.sync_api import Page, expect

from scripts._playwright_auth import login_via_auth_entry

APP_PATH = "/apps/audio-transcription"
TRANSCRIPT_ROUTE_READY_SELECTOR = '[data-test="transcript-workflow-rail-shell"]'
TRANSCRIPT_SUCCESS_SELECTOR = '[data-test="transcript-result-surface"]'
TRANSCRIPT_FAILED_SELECTOR = '[data-test="transcript-failed-surface"]'


def open_transcript_lane(
    page: Page,
    *,
    base_url: str,
    email: str,
    password: str,
    artifact_dir: Path,
) -> None:
    """Open the authenticated public Audio Transcription route."""

    login_via_auth_entry(
        page,
        base_url=base_url,
        email=email,
        password=password,
        next_path=APP_PATH,
        success_heading_pattern=r"Konvertera prov|Transkribera samtal|Välj inspelning|Valj inspelning",
        success_selector=TRANSCRIPT_ROUTE_READY_SELECTOR,
        recover_to_next_path=True,
        failure_artifacts_dir=artifact_dir,
        success_timeout_ms=60_000,
    )
    expect(page.locator(TRANSCRIPT_ROUTE_READY_SELECTOR)).to_be_visible(timeout=60_000)


def select_audio(page: Page, *, audio_path: Path, speaker_count: int) -> None:
    """Select a source audio fixture and speaker count in the route UI."""

    page.locator('[data-test="transcript-source-file-input"]').set_input_files(str(audio_path))
    page.locator('[data-test="transcript-speaker-mode-known"]').click()
    page.locator('[data-test="transcript-speaker-count"]').fill(str(speaker_count))


def start_transcript(page: Page) -> None:
    """Start the selected transcript job through the route UI."""

    expect(page.locator('[data-test="transcript-start"]')).to_be_enabled(timeout=30_000)
    page.locator('[data-test="transcript-start"]').click()


def reset_transcript(page: Page) -> None:
    """Reset transcript choices between retained proof attempts."""

    page.locator('[data-test="transcript-reset"]').click()
    expect(page.locator('[data-test="transcript-start"]')).to_be_disabled(timeout=30_000)


def wait_for_failed(page: Page, *, artifact_dir: Path, timeout_seconds: int) -> None:
    """Wait for the failed terminal surface and retain a screenshot."""

    _wait_for_terminal_surface(
        page,
        artifact_dir=artifact_dir,
        timeout_seconds=timeout_seconds,
        expected="failed",
        screenshot_name="transcript-failed.png",
    )


def wait_for_success(page: Page, *, artifact_dir: Path, timeout_seconds: int) -> None:
    """Wait for the succeeded terminal surface and retain a screenshot."""

    _wait_for_terminal_surface(
        page,
        artifact_dir=artifact_dir,
        timeout_seconds=timeout_seconds,
        expected="succeeded",
        screenshot_name="transcript-succeeded.png",
    )


def _wait_for_terminal_surface(
    page: Page,
    *,
    artifact_dir: Path,
    timeout_seconds: int,
    expected: str,
    screenshot_name: str,
) -> None:
    deadline = datetime.now(tz=UTC).timestamp() + timeout_seconds
    while datetime.now(tz=UTC).timestamp() < deadline:
        failed_visible = page.locator(TRANSCRIPT_FAILED_SELECTOR).count() > 0
        success_visible = page.locator(TRANSCRIPT_SUCCESS_SELECTOR).count() > 0
        if expected == "failed" and failed_visible:
            page.screenshot(path=str(artifact_dir / screenshot_name), full_page=True)
            return
        if expected == "succeeded" and success_visible:
            page.screenshot(path=str(artifact_dir / screenshot_name), full_page=True)
            return
        if expected == "succeeded" and failed_visible:
            page.screenshot(path=str(artifact_dir / "transcript-failed.png"), full_page=True)
            raise AssertionError("Transcript job failed in UI.")
        page.wait_for_timeout(2_000)
    page.screenshot(path=str(artifact_dir / f"transcript-{expected}-timeout.png"), full_page=True)
    raise AssertionError(f"Timed out waiting for transcript {expected}.")
