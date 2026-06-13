"""Conversion Hub saved transcript JSON contract helpers.

Domain purpose:
  Keep canonical transcript segment and speaker-label extraction consistent for
  durable transcript save, speaker overlays, and formatter replay preparation.

Relationships:
  - Used by Conversion Hub transcript save handlers before persistence.
  - Used by formatter replay handlers before overlay-aware export requests.
"""

from __future__ import annotations

from collections.abc import Mapping

from pydantic import JsonValue

from skriptoteket.domain.errors import validation_error

JsonObject = Mapping[str, JsonValue]


def transcript_mapping(transcript_json: JsonObject) -> JsonObject:
    """Return the nested transcript object when present, else the root payload."""
    return _mapping_value(transcript_json, "transcript") or transcript_json


def canonical_transcript_segments(transcript_json: JsonObject) -> list[JsonObject]:
    """Return strict, non-empty canonical segments accepted by saved transcripts.

    Raises:
        DomainError: If the transcript payload has no segment list or contains
            non-object segment entries.
    """
    transcript = transcript_mapping(transcript_json)
    segments = _segments_value(transcript_json=transcript_json, transcript=transcript)
    if not isinstance(segments, list) or not segments:
        raise validation_error("Transcript JSON must contain at least one segment.")
    canonical_segments: list[JsonObject] = []
    for segment in segments:
        if not isinstance(segment, Mapping):
            raise validation_error("Transcript JSON contains an invalid segment.")
        canonical_segments.append(segment)
    return canonical_segments


def canonical_speaker_labels(transcript_json: JsonObject) -> list[str]:
    """Return first-seen canonical speaker labels from validated transcript segments.

    Raises:
        DomainError: If any canonical segment is missing a speaker label.
    """
    labels: list[str] = []
    seen: set[str] = set()
    for segment in canonical_transcript_segments(transcript_json):
        label = string_value(segment, "speaker_label") or string_value(segment, "speakerLabel")
        if label is None or not label.strip():
            raise validation_error("Transcript JSON segments must contain speaker labels.")
        if label not in seen:
            seen.add(label)
            labels.append(label)
    return labels


def string_value(value: JsonObject, key: str) -> str | None:
    """Return a string field from a JSON object when the field has string type."""
    raw = value.get(key)
    return raw if isinstance(raw, str) else None


def _segments_value(
    *,
    transcript_json: JsonObject,
    transcript: JsonObject,
) -> JsonValue | None:
    segments = transcript.get("segments")
    if isinstance(segments, list):
        return segments
    return transcript_json.get("segments")


def _mapping_value(
    value: JsonObject,
    key: str,
) -> JsonObject | None:
    nested = value.get(key)
    return nested if isinstance(nested, Mapping) else None
