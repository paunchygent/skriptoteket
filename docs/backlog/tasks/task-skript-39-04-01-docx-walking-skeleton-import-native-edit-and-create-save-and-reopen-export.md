---
type: task
id: TASK-SKRIPT-39-04-01
title: 'DOCX walking skeleton: import, native edit and create, save and reopen, export'
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-09-05'
status: proposed
closeout_review:
  record: inline
  status: not_started
task_kind: story
acceptance_criteria:
- A real DOCX source converts end to end through deterministic extraction, teacher
  review, versioned Mina filer save and reopen, and on-demand QTI, PDF, and DOCX export
story: ST-SKRIPT-39-04
backlog_document_profile: contract-derived
---

## Implementation Contract

Build the smallest correct DOCX walking skeleton for the native editable
exam workspace: DOCX upload, deterministic paragraph/table/style extraction
into the source-neutral native exam document, per-item confidence, LLM
remainder parsing plus answer-key proposals through the existing
Luna/GLM-plus-lease line, teacher review/edit/create in a minimal workspace
surface, versioned save with assets and editing state in Mina filer, reopen,
and on-demand QTI and PDF export through the existing writers and
fail-closed validators, plus DOCX export through a minimal new writer with
validation (ST-SKRIPT-21-10 DOCX-contract slice).

- The fixture is a genuine unchanged teacher DOCX (real-source fixture
  requirement); synthetic-only proof does not qualify.
- The native document is source-neutral and does not mirror source-format
  internals into persistence. Correction-session review/versioning is the
  precedent to follow where it fits; Mina filer storage internals are
  decided during implementation; add no second state authority.
- Preserve the empirical Exam.net contract: QTI and PDF exports pass the
  existing validators unchanged; no new importer research, no unsupported
  types.

## Contract Inputs

- ST-SKRIPT-39-04 slice contract and terms S1-S5; EPIC-SKRIPT-39 terms
  E8-E12; ADR-SKRIPT-0091 (`proposed`).
- Required predecessors (required future state, each must be `done`):
  TASK-SKRIPT-39-02-03, TASK-SKRIPT-39-03-03, TASK-SKRIPT-39-03-04.
- Existing seams: `python-docx` dependency, QTI/PDF writers and validators,
  correction sessions, Mina filer, Luna/GLM lease line.
- New seam in this task: the minimal DOCX writer, validation, and
  file-action contract per the ST-SKRIPT-21-10 DOCX-contract slice.

## Core Vertical And Performance

The walking skeleton is:

`real DOCX upload -> deterministic extraction -> native exam document v1 ->
confidence-gated LLM remainder and answer-key proposals -> teacher
review/edit/create -> versioned Mina filer save -> reopen -> on-demand
QTI/PDF/DOCX export`.

State stays in the decided authorities: the native document persists in
Mina filer; jobs, enrichment, lease, and correction sessions stay in
PostgreSQL/UoW. Native-document storage internals are decided during
implementation. No extra polling layer or persistence authority is added.

## Validation

- A genuine unchanged DOCX fixture proves admission, deterministic
  extraction with per-item confidence, LLM proposals, teacher
  review/edit/create, versioned save, faithful reopen, validator-passing
  QTI/PDF exports, and a validated DOCX export.
- An authenticated live functional check through the real product surface
  is recorded in `handoff.md`; focused or synthetic checks alone do not
  satisfy this criterion.
- Backend gates per `AGENTS.md`: lint, typecheck, focused tests. Report
  them as supporting checks, never as the integrated proof.

## Stop Conditions

- Do not begin before TASK-SKRIPT-39-02-03, TASK-SKRIPT-39-03-03, and
  TASK-SKRIPT-39-03-04 are done.
- Do not begin before ADR-SKRIPT-0091 and ST-SKRIPT-39-04 leave `proposed`
  through review.
- Stop if the native model mirrors source-format internals into
  persistence.
- Stop if scanned/OCR input is offered a conversion path: OCR is deferred.
- Production file submission is not authorized; production acceptance
  remains with the user.

## Decided Contract Terms

| ID | Decided contract term |
| --- | --------------------- |
| D1 | One genuine unchanged DOCX fixture is the mandatory walking-skeleton input. |
| D2 | The native document lives in Mina filer; jobs, enrichment, lease, and correction sessions stay under PostgreSQL/UoW; storage internals are decided during implementation. |
| D3 | QTI and PDF exports pass the existing fail-closed validators unchanged; the minimal DOCX writer ships with validation. |
| D4 | Cleanup tasks and workspace review gates precede implementation. |
| D5 | Production acceptance remains user-owned. |
