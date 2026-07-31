---
type: task
id: TASK-SKRIPT-37-05-05
title: ST-SKRIPT-37-05 Audio Transcription export naming adoption
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: blocked
readiness_review:
  record: inline
  status: not_started
closeout_review:
  record: inline
  status: not_started
story: ST-SKRIPT-37-05
task_kind: story
acceptance_criteria:
- Given a transcript export is generated, when TXT, Markdown, VTT, or SRT is downloaded
  or saved, then the default filename includes source transcript provenance, the canonical
  `Transkribering` output-purpose label, and exactly one correct extension.
- Given the transcript export is producer-replay-owned, when naming is applied, then
  Skriptoteket records teacher-facing name intent without taking browser or producer
  artifact authority.
- Given the teacher edits the filename stem before download or save, when the action
  completes, then the selected format and extension remain consistent and the UI consumes
  the final sanitized filename returned by the protected API.
---

## Context

The source does not provide a separate context section; no additional context is recorded.

## Decision And Assumption Ledger

The source does not provide a separate decision and assumption ledger section; no additional decision and assumption ledger is recorded.

## Story Contract Slice

### Source: Goal

Adopt the shared naming contract for Audio Transcription downloads and
`Mina filer` saves.

## Contract Inputs

The source does not provide a separate contract inputs section; no additional contract inputs is recorded.

## Plan

### Source: Implementation Plan

1. Map saved transcript source title and selected export format to the shared
   naming contract and canonical `Transkribering` label.
2. Add editable stem support before download/save.
3. Preserve producer-replay artifact authority while keeping the protected API
   authoritative for final filename metadata.
4. Add tests for repeated extensions, canonical purpose vocabulary,
   source naming, and save/download parity without browser-side reconstruction.

## Implementation Steps

The source does not provide a separate implementation steps section; no additional implementation steps is recorded.

## Proof

### Source: Test Plan

- Focused backend/frontend transcript export tests, including canonical purpose
  labels and protected API filename parity.
- `pdm run fe-type-check`
- `pdm run fe-lint`
- Relevant backend gates if API handlers change.
- `pdm run docs-validate`
- `git diff --check`

## Validation

The source does not provide a separate validation section; no additional validation is recorded.

## Stop Conditions

### Source: Non-goals

- No transcript replay architecture change.
- No speaker overlay persistence change.
- No new export formats.

### Source: Rollback Plan

Revert transcript naming adoption and keep existing export behavior.

## Lessons Learned

The source does not provide a separate lessons learned section; no additional lessons learned is recorded.

## Notes

The source does not provide a separate notes section; no additional notes is recorded.

### Source: PR-0394: ST-37-05 Audio Transcription Export Naming Adoption



### Source: Problem

Transcript export names can be redundant or hard to connect to the source
transcript.

## Plan Document Review

The source does not provide a separate plan document review section; no additional plan document review is recorded.

## Implementation Review

The source does not provide a separate implementation review section; no additional implementation review is recorded.
