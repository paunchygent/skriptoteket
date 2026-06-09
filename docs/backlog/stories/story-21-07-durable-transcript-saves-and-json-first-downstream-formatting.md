---
type: story
id: ST-21-07
title: "Durable transcript saves and JSON-first downstream formatting"
status: ready
owners: "agents"
created: 2026-06-09
updated: 2026-06-09
epic: "EPIC-21"
dependencies:
  - "ST-21-06"
  - "Sir Convert Story 54"
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

Implementation remains blocked on canonical JSON/Sir Convert Story 54. The
story may plan the saved transcript contract now, but formatter work must wait
for canonical JSON authority.

This story owns the durable product handoff: preserving canonical JSON
authority, provenance, and optional downstream formatter outputs without
turning Skriptoteket into an STT runtime.

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
- Preserve JSON-first formatter sequencing before TXT/Markdown/VTT/SRT work.
- Derive future TXT/Markdown/VTT/SRT views only from canonical JSON or Sir
  Convert formatter artifacts.
- Keep logs and metrics content-safe.

## Non-Goals

- No source audio or normalized audio durable archive unless a separate product
  decision accepts it.
- No local STT, diarization, alignment, or re-transcription.
- No formatter work before canonical JSON is stable.
- No public/no-login durable transcript storage.

## Upstream Dependencies

- Sir Convert formatter story:
  `/Users/olofs_mba/Documents/Repos/sir-convert-a-lot/docs/backlog/stories/story-54-transcript-formatter-strategies-over-canonical-json.md`
- Sir Convert route contract:
  `/Users/olofs_mba/Documents/Repos/sir-convert-a-lot/docs/converters/audio-transcription-service-api-artifact-contract.md`

## Notes

- A later PR slice should decide whether saved transcripts are ordinary user
  files, a typed transcript aggregate, or both. That choice must include access,
  retention, delete/export, and search/indexing behavior.
