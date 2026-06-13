---
type: story
id: ST-21-07
title: "Durable transcript saves and JSON-first downstream formatting"
status: done
owners: "agents"
created: 2026-06-09
updated: 2026-06-13
epic: "EPIC-21"
dependencies:
  - "ST-21-06"
  - "Sir Convert Task 356"
  - "Sir Convert Story 54 / Task 358 for product-neutral formatter outputs"
acceptance_criteria:
  - "Given `transcript_json` is available, when the teacher saves it, then Skriptoteket persists an owner-scoped user file or transcript record with source, job, artifact, schema, language, diarization setting, and speaker-setting provenance."
  - "Given Sir Convert retention is short, when a teacher has not saved the transcript, then Skriptoteket does not imply durable availability after the Sir Convert job/artifact TTL."
  - "Given downstream formatting is requested, when TXT, Markdown, VTT, or SRT is produced, then it is derived only from canonical saved JSON or Sir Convert formatter artifacts and never by re-transcribing or inventing parallel transcript truth."
  - "Given transcript content can contain sensitive user content, when Skriptoteket logs, lists, or reports transcript jobs, then it avoids transcript text, utterances, source filenames as labels, media hashes as labels, and model/provider details."
ui_impact: "Yes (teachers can save transcript results and later work from durable JSON-first transcript records)."
data_impact: "Yes (new owner-scoped durable transcript artifact or file metadata owned by Skriptoteket)."
---

# ST-21-07: Durable Transcript Saves And JSON-First Downstream Formatting

## Context

Sir Convert ADR-0013 keeps uploaded recordings, normalized audio, and transcript
artifacts under short operational retention. Product-facing durable transcript
retention belongs in Skriptoteket after the teacher saves a transcript.
Put plainly: durable transcript retention belongs in Skriptoteket after save.

Durable JSON save work started after Sir Convert Task 356 and Review 42 because
canonical `transcript_json` runtime behavior is accepted. Sir Convert Story 54
and Task 358 are now accepted for product-neutral TXT, Markdown, WebVTT, and
SRT formatter artifacts over canonical JSON.

This story owns the durable product handoff: preserving canonical JSON
authority, provenance, and optional downstream formatter outputs without
turning Skriptoteket into an STT runtime.

Post-save speaker naming and overlay-aware exports are not part of `ST-21-07`.
They are governed by `ST-21-08` and Sir Convert Story 56.

## Scope

- Persist saved transcript JSON or an owner-scoped transcript file/record.
- Preserve provenance:
  - Sir Convert job id or local owned job reference;
  - artifact key;
  - transcript schema version;
  - source filename metadata where safe;
  - language evidence;
  - diarization mode and speaker controls;
  - generation timestamp and correlation id where appropriate.
- Make saved transcripts available after Sir Convert's operational TTL expires.
- Preserve JSON-first formatter sequencing for TXT/Markdown/VTT/SRT work.
- Derive future TXT/Markdown/VTT/SRT views only from canonical JSON, accepted
  Sir Convert formatter artifacts, or the accepted Sir Convert overlay replay
  route.
- Keep logs and metrics content-safe.

## Non-Goals

- No source audio or normalized audio durable archive unless a separate product
  decision accepts it.
- No local STT, diarization, alignment, or re-transcription.
- No overlay-aware formatter replay, download, or Mina filer save work in this
  story.
- No public/no-login durable transcript storage.

## Upstream Dependencies

- Sir Convert canonical JSON runtime task:
  `/Users/olofs_mba/Documents/Repos/sir-convert-a-lot/docs/backlog/tasks/task-356-execute-audio-transcript-jobs-and-persist-canonical-transcript-json.md`
- Sir Convert formatter story:
  `/Users/olofs_mba/Documents/Repos/sir-convert-a-lot/docs/backlog/stories/story-54-transcript-formatter-strategies-over-canonical-json.md`
- Sir Convert overlay replay story:
  `/Users/olofs_mba/Documents/Repos/sir-convert-a-lot/docs/backlog/stories/story-56-transcript-speaker-overlay-formatter-replay-over-canonical-json.md`
- Sir Convert route contract:
  `/Users/olofs_mba/Documents/Repos/sir-convert-a-lot/docs/converters/audio-transcription-service-api-artifact-contract.md`

## Implementation Slices

- `PR-0343` owns the durable saved `transcript_json` boundary after the
  Gateway-backed lifecycle client retrieves a valid transcript artifact. It is
  done as of 2026-06-12 with a typed saved-transcript aggregate, authenticated
  save/readback API, frontend save affordance, and approved retained review
  `REV-PR-0343`.

## Notes

- `PR-0343` chose a typed transcript aggregate backed by the existing
  Conversion Hub job ledger. Saved transcript management can now build list,
  open, delete, export, and search/indexing behavior from this record shape.
- Post-`PR-0343` scaffolding now continues in `ST-21-08`: progress/cancel
  parity, speaker-name overlays, overlay-aware formatter replay, and
  download/Mina filer save actions.
- Formatter/export implementation is no longer blocked on Story 54 authority;
  overlay-aware exports remain blocked on Sir Convert Story 56 and HuleEdu
  `ST-01-09` until those replay/Gateway tasks land.
