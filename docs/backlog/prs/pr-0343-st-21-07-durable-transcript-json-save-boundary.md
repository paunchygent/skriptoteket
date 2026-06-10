---
type: pr
id: PR-0343
title: "ST-21-07 Durable transcript JSON save boundary"
status: ready
owners: "agents"
created: 2026-06-10
updated: 2026-06-10
stories:
  - "ST-21-07"
tags:
  - backend
  - frontend
  - conversion-hub
  - transcript
  - user-files
  - provenance
dependencies:
  - "PR-0342"
  - "Sir Convert Task 356"
acceptance_criteria:
  - "Given a valid `transcript_json` artifact is available through Gateway, when the teacher saves it, then Skriptoteket persists an owner-scoped transcript record or user file with schema, source/job/artifact provenance, language evidence, diarization mode, speaker controls, generation timestamp, and correlation metadata."
  - "Given Sir Convert's operational artifact retention expires, when a saved transcript is opened later, then Skriptoteket serves the durable saved JSON record rather than relying on the upstream job artifact."
  - "Given an unsaved transcript job exists, when the UI describes availability, then it does not imply durable storage after Sir Convert TTL."
  - "Given transcript content may contain sensitive user content, when the backend logs, lists, or reports saves, then it excludes transcript text, utterances, source filenames as labels, media hashes as labels, and provider/model details."
  - "Given TXT, Markdown, VTT, or SRT output is requested, when this PR closes, then those formatters remain unavailable unless backed by canonical saved JSON or a later accepted Sir Convert formatter artifact."
---

# PR-0343: ST-21-07 Durable Transcript JSON Save Boundary

## Problem

Sir Convert keeps recordings, normalized audio, and transcript artifacts under
short operational retention. Skriptoteket needs a durable, owner-scoped product
save boundary for canonical transcript JSON after teachers choose to save a
result.

## Goal

Persist validated `transcript_json` from `PR-0342` as Skriptoteket-owned
teacher content with provenance, access control, retention, and deletion
behavior that does not depend on Sir Convert's short artifact TTL.

## Non-goals

- No durable source-audio archive.
- No local STT, diarization, alignment, transcript repair, or re-transcription.
- No TXT, Markdown, VTT, or SRT formatter implementation in this PR.
- No public/no-login durable transcript storage.

## Implementation Plan

1. Decide the durable aggregate shape inside this PR: typed transcript record,
   user-file metadata, or a user-file backed transcript aggregate.
2. Add backend domain/application contracts for saved transcript JSON,
   provenance, owner-scoped access, validation, and delete/export behavior.
3. Add infrastructure persistence behind repository protocols and Unit of Work;
   repositories must not commit.
4. Add API endpoints or reuse existing user-file save surfaces only when they
   preserve transcript provenance and owner checks.
5. Extend the frontend transcript lane with save/readback affordances that make
   unsaved upstream TTL limitations clear.
6. Keep formatter affordances unavailable until a later formatter authority
   exists.

## Test Plan

- Red-first backend tests for owner-scoped save, readback, invalid JSON
  rejection, provenance retention, and delete/export behavior.
- Red-first API tests proving cross-owner access fails closed.
- Red-first frontend tests for save affordance, saved/readback state, upstream
  TTL copy, and formatter-unavailable behavior.
- `pdm run lint`
- `pdm run typecheck`
- Focused backend pytest for transcript save APIs and repository behavior.
- Focused frontend Vitest for transcript save/readback views.
- `pdm run docs-validate`
- `pdm run handoff-validate`
- `git diff --check`

## Rollback Plan

Hide save/readback affordances and leave `PR-0342` as transient transcript job
retrieval only. Do not preserve transcript text in logs or temporary local
fallback storage.
