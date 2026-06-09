---
type: story
id: ST-21-06
title: "Transcript job lifecycle through HuleEdu Gateway"
status: ready
owners: "agents"
created: 2026-06-09
updated: 2026-06-09
epic: "EPIC-21"
dependencies:
  - "ST-21-05"
  - "HuleEdu ST-01-08"
  - "Sir Convert Story 53"
acceptance_criteria:
  - "Given a valid audio upload and diarization options, when the teacher submits, then Skriptoteket calls HuleEdu Gateway `/sir-convert/v2/convert/jobs` with route `audio -> transcript_bundle`, `audio_transcription_options`, CSRF, idempotency, and correlation headers."
  - "Given a transcript job is running, when Skriptoteket polls through Gateway, then the UI renders status, stage, heartbeat, processed seconds, total seconds, chunk progress, and retry/cancel states when available."
  - "Given the job succeeds, when Skriptoteket retrieves artifacts, then it fetches named artifact `transcript_json` through Gateway and treats missing, empty, undiarized, or unaligned JSON as failure rather than success."
  - "Given Gateway or Sir Convert returns admission, capacity, media safety, diarization, alignment, retention, or auth errors, when Skriptoteket renders them, then teacher-facing copy avoids provider/model/internal-service details."
ui_impact: "Yes (authenticated transcript jobs gain progress, cancel/error handling, and transcript artifact retrieval)."
data_impact: "Transient job ledger/status only; durable transcript persistence is ST-21-07."
---

# ST-21-06: Transcript Job Lifecycle Through HuleEdu Gateway

## Context

Skriptoteket already uses HuleEdu Gateway for authenticated Sir Convert
artifact-bundle work in the Exam Converter lane. Speech-to-text should reuse
that product edge instead of adding direct Sir Convert browser calls or
Skriptoteket-owned STT runtime logic.

This story owns the transcript job lifecycle from submit through canonical JSON
artifact retrieval. It is blocked on Sir Convert route registration and HuleEdu
Gateway support for the accepted audio route.

Implementation remains blocked on Sir Convert Story 53 and HuleEdu ST-01-08.
Until both are accepted and available, this story is planning authority only and
does not authorize a local transcript runtime or direct Sir Convert access.

## Scope

- Build a Gateway-backed transcript job submission client over
  `/sir-convert/v2/convert/jobs`.
- Preserve CSRF, idempotency, and correlation behavior.
- Poll job status/result/artifact surfaces through Gateway.
- Render route-specific audio progress fields when Sir Convert exposes them.
- Support cancel where the upstream route supports cancel.
- Retrieve `transcript_json` as the canonical transcript authority.
- Treat false-success shapes as failures:
  - missing JSON artifact;
  - empty transcript;
  - missing speaker labels;
  - diarization unavailable;
  - failed alignment.

## Non-Goals

- No public transcript job path.
- No public/no-login/direct Sir Convert browser/sidecar access.
- No durable transcript save in this story.
- No re-transcription or local diarization fallback.

## Upstream Dependencies

- Sir Convert route execution story:
  `/Users/olofs_mba/Documents/Repos/sir-convert-a-lot/docs/backlog/stories/story-53-audio-transcript-bundle-route-execution-and-json-artifact-persistence.md`
- HuleEdu Gateway story:
  `/Users/olofs_mba/Documents/Repos/huleedu/docs/backlog/stories/story-01-08-expose-sir-convert-audio-transcription-jobs-through-huleedu-auth-edge.md`

## Notes

- The UI should surface progress as work done and next action, not expose
  internal stages as implementation jargon.
- Artifact reads must remain owner-scoped through Gateway identity. Raw upstream
  job ids are not the teacher-facing authorization boundary.
