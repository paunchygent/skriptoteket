"""Audio Transcription parity progress snapshot contract tests.

Domain purpose:
    Protect the native transcript live proof from requiring removed raw progress
    counters while still demanding honest progress evidence before export proof.

Relationships:
    Exercises the Audio Transcription parity proof entrypoint's progress snapshot
    predicate without launching a browser or contacting HuleEdu/Sir Convert.
"""

from __future__ import annotations

from pathlib import Path

from scripts.audio_transcription_parity_live import (
    _capture_progress_snapshot,
    _progress_snapshot_has_evidence,
)


class _FakeLocator:
    def __init__(self, *, text: str | None = None, visible: bool = False, count: int = 0) -> None:
        self._text = text
        self._visible = visible
        self._count = count

    @property
    def first(self) -> "_FakeLocator":
        return self

    def count(self) -> int:
        return self._count

    def is_visible(self) -> bool:
        return self._visible

    def inner_text(self, *, timeout: int) -> str:
        return self._text or ""


class _FakePage:
    def __init__(self, locators: dict[str, _FakeLocator]) -> None:
        self.locators = locators
        self.screenshots: list[str] = []

    def locator(self, selector: str) -> _FakeLocator:
        return self.locators.get(selector, _FakeLocator())

    def screenshot(self, *, path: str, full_page: bool) -> None:
        self.screenshots.append(path)
        Path(path).write_bytes(b"png")

    def wait_for_timeout(self, timeout: int) -> None:
        raise AssertionError("terminal fast-completion test should not poll")


def _snapshot(**overrides: object) -> dict[str, object]:
    values: dict[str, object] = {
        "running_visible": True,
        "phase_visible": True,
        "phase_text": "Skriver ut samtalet",
        "steps_visible": False,
        "current_step_visible": False,
        "percent_visible": False,
        "upload_bytes_visible": False,
        "duration_visible": False,
        "chunks_visible": False,
        "heartbeat_visible": False,
    }
    values.update(overrides)
    return values


def test_job_progress_accepts_phase_with_workflow_steps_without_raw_counters() -> None:
    snapshot = _snapshot(
        steps_visible=True,
        current_step_visible=True,
        percent_visible=False,
        duration_visible=False,
        chunks_visible=False,
        heartbeat_visible=False,
    )

    assert _progress_snapshot_has_evidence(snapshot) is True


def test_upload_progress_accepts_phase_with_upload_percent_or_bytes() -> None:
    percent_snapshot = _snapshot(
        phase_text="Laddar upp inspelningen.",
        percent_visible=True,
    )
    bytes_snapshot = _snapshot(
        phase_text="Laddar upp inspelningen.",
        upload_bytes_visible=True,
    )

    assert _progress_snapshot_has_evidence(percent_snapshot) is True
    assert _progress_snapshot_has_evidence(bytes_snapshot) is True


def test_progress_snapshot_rejects_phase_without_user_visible_progress_evidence() -> None:
    assert _progress_snapshot_has_evidence(_snapshot()) is False


def test_terminal_before_snapshot_is_reported_by_capture_not_progress_predicate() -> None:
    snapshot = _snapshot(
        phase_visible=False,
        phase_text=None,
        terminal_reached_before_snapshot=True,
    )

    assert _progress_snapshot_has_evidence(snapshot) is False


def test_capture_progress_allows_terminal_before_snapshot_fast_completion(tmp_path: Path) -> None:
    page = _FakePage(
        {
            '[data-test="transcript-result-surface"]': _FakeLocator(
                visible=True,
                count=1,
            ),
        }
    )

    snapshot = _capture_progress_snapshot(page, artifact_dir=tmp_path, timeout_seconds=1)

    assert snapshot["terminal_reached_before_snapshot"] is True
    assert page.screenshots == [str(tmp_path / "progress-terminal-before-snapshot.png")]
