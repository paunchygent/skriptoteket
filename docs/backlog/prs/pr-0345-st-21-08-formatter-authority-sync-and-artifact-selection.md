---
type: pr
id: PR-0345
title: "ST-21-08 Formatter authority sync and artifact selection"
status: done
owners: "agents"
created: 2026-06-13
updated: 2026-06-13
stories:
  - "ST-21-08"
tags:
  - frontend
  - api
  - conversion-hub
  - transcript
  - formatter
dependencies:
  - "PR-0343"
  - "Sir Convert Task 358"
acceptance_criteria:
  - "Given Sir Convert Task 358 is accepted, when Skriptoteket docs and generated contracts are updated, then TXT, Markdown, VTT, and SRT are no longer described as blocked by formatter authority."
  - "Given transcript artifact selection is represented in code, when artifact formats are requested, then only closed typed values for `json`, `txt`, `md`, `vtt`, and `srt` are accepted for audio jobs."
  - "Given overlay-aware replay is not yet implemented, when this PR closes, then Skriptoteket still does not locally format saved transcripts or expose overlay-aware export actions."
  - "Given generated Sir Convert DTOs change, when parsers and tests are updated, then no loose strings, catch-all artifact maps, compatibility aliases, or wrapper shims are introduced."
---

# PR-0345: ST-21-08 Formatter Authority Sync And Artifact Selection

## Problem

Skriptoteket still contains planning text and generated assumptions from before
Sir Convert Story 54 / Task 358 was accepted.

## Goal

Align Skriptoteket with the accepted product-neutral formatter authority while
keeping overlay-aware product exports behind the replay contract.

## Non-goals

- No speaker overlay persistence.
- No replay client.
- No download or Mina filer save actions for formatter artifacts.
- No local formatter implementation.

## Implementation Plan

Implemented on 2026-06-13.

- Removed stale formatter-blocked semantics from the docs guard and kept
  ST-21-07 / EPIC-21 / PR-0343 aligned with accepted Sir Convert Task 358.
- Added closed transcript artifact values for `json`, `txt`, `md`, `vtt`, and
  `srt`, named transcript artifact keys, transcript-specific artifact
  availability, and content-type validation.
- Kept default transcript submission JSON-first while allowing typed formatter
  artifact selection for future replay/download slices.
- Rejected stale `not_implemented` transcript formatter manifests instead of
  carrying a compatibility alias or shim.

## Test Plan

- `pdm run pytest tests/unit/scripts/test_conversion_hub_transcript_docs_guard.py`
- `pdm run fe-test -- src/api/sirConvertGateway/transcriptOptions.spec.ts src/api/sirConvertGateway/transcriptClient.spec.ts`

## Rollback Plan

Revert artifact selection UI/client exposure while preserving the corrected
docs fact that Sir Convert Task 358 is accepted.
