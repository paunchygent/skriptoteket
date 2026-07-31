---
type: story
id: ST-SKRIPT-26-02
title: Klassrumskartan — Class-list import from file with teacher preview and confirmation
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: ready
readiness_review:
  record: inline
  status: not_started
closeout_review:
  record: inline
  status: not_started
epic: EPIC-SKRIPT-26
acceptance_criteria:
- Given a teacher uploads an `XLSX`, `TXT`, or `PDF` file for class-list import, when
  the file is processed, then Skriptoteket returns a suggested class-list name plus
  a parsed list of students for teacher review before save.
- Given the uploaded file is a PDF, when parsing runs, then Klassrumskartan uses Sir
  Convert-a-Lot through the fast parsing lane and does not rely on the heavier default
  parsing path.
- Given PDF parsing runs through Sir Convert-a-Lot, when service routing is chosen,
  then the Hule internal-network lane is preferred where available and external/public
  access remains a fallback.
- Given the parsed student list contains ambiguities or noisy rows, when the preview
  is shown, then the teacher can correct or reject the proposed class list before
  any class roster is created or updated.
- Given the uploaded roster contains blank rows, duplicate-looking rows, or rows that
  cannot be mapped confidently to a student name, when preview is shown, then those
  rows are surfaced explicitly for teacher confirmation rather than silently dropped
  into the saved class roster.
- Given the teacher confirms the import preview, when the save completes, then the
  resulting class roster follows the normal Klassrumskartan class-first workflow without
  introducing hidden metadata expansion.
- Given the import story ships, when a file cannot be parsed confidently, then the
  teacher receives a clear preview-state failure or partial-result flow instead of
  silent roster creation.
retired_ids:
- ST-26-02
---

## Context

### Source: Context

Teachers often start from an existing roster document rather than by manually typing students. Import belongs in the same teacher I/O lane as explicit exports, but it must stay bounded, preview-first, and separate from future smart-planning concerns.

## Epic Contract Slice

The independently reviewable behavior is represented by the source context, goal, and implementation material above.

## ADR Coverage

No separate ADR coverage was recorded in the source snapshot.

## Contract Inputs

No separate contract inputs were recorded in the source snapshot.

## Live Verification Plan

Verification follows the acceptance and verification material recorded above.

## Non-Goals

No separate non-goals were recorded in the source snapshot.

## Notes

### Source: Notes

- `XLSX` is the primary import format.
- `TXT` is the lightweight fallback.
- `PDF` parsing should go through Sir Convert-a-Lot as a service dependency rather than through new heavy parsing logic inside Skriptoteket.
- This story is about roster ingestion, not student metadata enrichment.
- Keep service integration bounded to roster extraction and normalization, not broad conversion-hub workflow ownership.

## Decision And Assumption Ledger

The source snapshot is the governing record for the decisions and assumptions stated above.

## Plan Document Review

No separate plan document review was recorded in the source snapshot.

## Story Closeout Review

No separate closeout review was recorded in the source snapshot.
