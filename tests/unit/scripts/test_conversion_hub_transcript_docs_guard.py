"""Guards the Conversion Hub transcript planning lane.

Purpose:
    Keep the downstream STT transcript stories aligned with Sir Convert and
    HuleEdu Gateway planning authority before any runtime implementation starts.

Relationships:
    - Reads the EPIC-21 transcript stories as governed docs-as-code artifacts.
    - Protects the approved retained review surface for ST-21-05 through
      ST-21-07.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BACKLOG = ROOT / "docs" / "backlog"

STORY_21_05 = (
    BACKLOG / "stories" / "story-21-05-conversion-hub-transcript-intake-and-diarization-controls.md"
)
STORY_21_06 = (
    BACKLOG / "stories" / "story-21-06-transcript-job-lifecycle-through-huleedu-gateway.md"
)
STORY_21_07 = (
    BACKLOG
    / "stories"
    / "story-21-07-durable-transcript-saves-and-json-first-downstream-formatting.md"
)
REVIEW = BACKLOG / "reviews" / "review-st-21-05-through-st-21-07-transcript-downstream-planning.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_transcript_lane_records_gateway_only_access_and_no_local_runtime() -> None:
    story_21_05 = _read(STORY_21_05)
    story_21_06 = _read(STORY_21_06)
    story_21_07 = _read(STORY_21_07)
    lane_text = "\n".join([story_21_05, story_21_06, story_21_07])

    assert "Gateway-only `/sir-convert/v2/convert` access" in lane_text
    assert "no public/no-login/direct Sir Convert browser/sidecar access" in lane_text
    assert "Skriptoteket-owned STT/diarization runtime" in lane_text
    assert "No local STT, diarization, alignment, or re-transcription." in story_21_07


def test_transcript_lane_records_diarization_and_blocked_sequencing() -> None:
    story_21_05 = _read(STORY_21_05)
    story_21_06 = _read(STORY_21_06)
    story_21_07 = _read(STORY_21_07)

    assert "`auto`" in story_21_05
    assert "`known_speaker_count`" in story_21_05
    assert "`speaker_range`" in story_21_05
    assert "min/max speaker range" in story_21_05
    assert "blocked on Sir Convert Story 53 and HuleEdu ST-01-08" in story_21_06
    assert "blocked on canonical JSON/Sir Convert Story 54" in story_21_07
    assert "durable transcript retention belongs in Skriptoteket after save" in story_21_07
    assert "JSON-first formatter sequencing" in story_21_07


def test_transcript_lane_has_approved_retained_review_gate() -> None:
    review = _read(REVIEW)

    assert "id: REV-ST-21-05" in review
    assert "status: approved" in review
    assert "stories:" in review
    assert "- ST-21-05" in review
    assert "- ST-21-06" in review
    assert "- ST-21-07" in review
    assert "Verdict:** approved" in review
