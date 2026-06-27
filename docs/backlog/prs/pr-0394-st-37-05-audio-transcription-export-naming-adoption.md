---
type: pr
id: PR-0394
title: "ST-37-05 Audio Transcription export naming adoption"
status: blocked
owners: "agents"
created: 2026-06-26
updated: 2026-06-27
stories:
  - "ST-37-05"
tags:
  - frontend
  - backend
  - audio-transcription
  - exports
dependencies:
  - "PR-0390"
  - "PR-0391"
  - "PR-0392"
acceptance_criteria:
  - "Given a transcript export is generated, when TXT, Markdown, VTT, or SRT is downloaded or saved, then the default filename includes source transcript provenance, the canonical `Transkribering` output-purpose label, and exactly one correct extension."
  - "Given the transcript export is producer-replay-owned, when naming is applied, then Skriptoteket records teacher-facing name intent without taking browser or producer artifact authority."
  - "Given the teacher edits the filename stem before download or save, when the action completes, then the selected format and extension remain consistent and the UI consumes the final sanitized filename returned by the protected API."
---

# PR-0394: ST-37-05 Audio Transcription Export Naming Adoption

## Problem

Transcript export names can be redundant or hard to connect to the source
transcript.

## Goal

Adopt the shared naming contract for Audio Transcription downloads and
`Mina filer` saves.

## Non-goals

- No transcript replay architecture change.
- No speaker overlay persistence change.
- No new export formats.

## Implementation Plan

1. Map saved transcript source title and selected export format to the shared
   naming contract and canonical `Transkribering` label.
2. Add editable stem support before download/save.
3. Preserve producer-replay artifact authority while keeping the protected API
   authoritative for final filename metadata.
4. Add tests for repeated extensions, canonical purpose vocabulary,
   source naming, and save/download parity without browser-side reconstruction.

## Test Plan

- Focused backend/frontend transcript export tests, including canonical purpose
  labels and protected API filename parity.
- `pdm run fe-type-check`
- `pdm run fe-lint`
- Relevant backend gates if API handlers change.
- `pdm run docs-validate`
- `git diff --check`

## Rollback Plan

Revert transcript naming adoption and keep existing export behavior.
