---
type: story
id: ST-21-05
title: "Conversion Hub transcript intake and diarization controls"
status: ready
owners: "agents"
created: 2026-06-09
updated: 2026-06-09
epic: "EPIC-21"
dependencies:
  - "ST-21-01"
  - "ST-21-03"
  - "HuleEdu ST-01-08"
  - "Sir Convert ADR-0013"
  - "Sir Convert Epic 12"
acceptance_criteria:
  - "Given a signed-in teacher opens `documents.conversion_hub`, when they choose transcript mode, then Skriptoteket offers an authenticated audio/video upload workflow and does not expose public or no-login STT."
  - "Given speaker controls are shown, when the teacher selects auto, exact count, or min/max range, then the UI maps to Sir Convert `auto`, `known_speaker_count`, or `speaker_range` and rejects invalid combinations before submit."
  - "Given an upload is invalid, unsupported, over the Sir Convert route policy, or not yet allowed by runtime registration, when the teacher submits, then Skriptoteket shows teacher-facing validation without backend model names, provider names, or service jargon."
  - "Given Sir Convert retention is short and operational, when the intake UI describes transcript availability, then it does not imply durable storage until the teacher saves the transcript in Skriptoteket."
ui_impact: "Yes (Conversion Hub gains an authenticated transcript intake mode with audio/video upload and speaker controls)."
data_impact: "No durable transcript persistence in this story; upload/job state remains transient until ST-21-07."
---

# ST-21-05: Conversion Hub Transcript Intake And Diarization Controls

## Context

Sir Convert ADR-0013 accepts sidecar-backed speech-to-text and the planned
`audio -> transcript_bundle` Service API v2 route. Skriptoteket owns the
teacher-facing Conversion Hub experience and durable transcript retention after
save. Sir Convert owns media safety, STT/diarization, short operational
retention, and canonical `transcript_json` artifact production.

This story starts the authenticated Skriptoteket product lane before runtime
implementation by defining the intake UX and client-side validation boundary.
It does not implement public/no-login transcription and does not create a
parallel transcription engine inside Skriptoteket.

The downstream access contract is Gateway-only `/sir-convert/v2/convert` access.
The transcript lane explicitly carries no public/no-login/direct Sir Convert browser/sidecar access
and no Skriptoteket-owned STT/diarization runtime.

## Scope

- Add a transcript mode under the authenticated `documents.conversion_hub`
  curated app.
- Accept governed audio files and video containers with audio streams only
  through the HuleEdu Gateway `/sir-convert/v2/convert/...` product edge.
- Provide diarization controls:
  - automatic speaker discovery mapped to Sir Convert `auto`;
  - known number of speakers mapped to `known_speaker_count`;
  - min/max speaker range mapped to `speaker_range`.
- Validate invalid speaker combinations locally before submit.
- Render upload/route-policy errors in teacher-facing language.
- Keep all backend/model/provider details out of UI copy.

## Non-Goals

- No public or anonymous STT route.
- No direct Sir Convert service credentials in browser code.
- No direct `convert.hule.education` product traffic.
- No transcript durable persistence until ST-21-07.
- No TXT/MD/VTT/SRT formatter assumptions before canonical JSON is stable.

## Upstream Dependencies

- Sir Convert ADR:
  `/Users/olofs_mba/Documents/Repos/sir-convert-a-lot/docs/decisions/0013-speech-to-text-sidecar-and-audio-ingestion-governance.md`
- Sir Convert route contract:
  `/Users/olofs_mba/Documents/Repos/sir-convert-a-lot/docs/converters/audio-transcription-service-api-artifact-contract.md`
- HuleEdu Gateway story:
  `/Users/olofs_mba/Documents/Repos/huleedu/docs/backlog/stories/story-01-08-expose-sir-convert-audio-transcription-jobs-through-huleedu-auth-edge.md`

## Notes

- The first implementation task should wait until Sir Convert Story 51 defines
  concrete route-level concurrency/admission caps.
- Teacher copy should say what the teacher can do next, not expose STT model,
  diarization backend, Gateway, or sidecar terminology.
