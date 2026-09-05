---
type: story
id: ST-SKRIPT-39-04
title: Native editable exam workspace with DOCX-first walking skeleton
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-09-05'
status: proposed
closeout_review:
  record: inline
  status: not_started
epic: EPIC-SKRIPT-39
acceptance_criteria:
- A teacher imports a DOCX source, reviews and edits questions, creates items from
  scratch, saves and reopens a versioned native exam document in Mina filer, and exports
  QTI, PDF, and DOCX on demand
links:
  decisions:
  - ADR-SKRIPT-0090
  - ADR-SKRIPT-0091
backlog_document_profile: contract-derived
---

## Slice Contract

Stand up the native editable exam workspace as one vertical slice, DOCX
first: a teacher uploads a DOCX source, deterministic-first parsing builds a
source-neutral native exam document, per-item confidence routes the
low-confidence remainder to LLM parsing and repair, the existing
answer-key-enrichment line proposes keys, and the teacher reviews, edits
existing questions, and creates items from scratch. The teacher saves a
versioned native document with assets and editing state in Mina filer,
reopens it, continues editing, and exports QTI and PDF on demand through
the existing fail-closed validators plus DOCX through a minimal new writer
with validation (ST-SKRIPT-21-10 DOCX-contract slice).

- The native document model is source-neutral: it carries items, assets,
  editing state, and provenance, and saves versioned in Mina filer. It
  reuses IR item semantics without mirroring source-format internals.
  Storage internals beyond Mina filer persistence are decided during
  implementation.
- Review and editing state follow the correction-session versioning and
  review precedent (version-conflict guard) where it fits. No second queue,
  filesystem state, or compatibility path is added.
- The item contract is the confirmed supported types on the Exam.net-proven
  subset; no unsupported-type handling is authorized. Unresolved DOCX
  content stays teacher-reviewable. No new importer research.
- Out of this slice: digital-PDF intake (follows as the next slice),
  OCR/scanned-PDF handling (deferred, undecided), QTI import (epic story 7),
  native-format internals beyond what the walking skeleton needs.

## Contract Inputs

- EPIC-SKRIPT-39 workspace terms E8-E12 and ADR-SKRIPT-0091 (`proposed`);
  ADR-SKRIPT-0090 generic-extraction boundary unchanged.
- Completed lanes the slice builds on: ST-SKRIPT-39-01 (in-process
  conversion + QTI/PDF exporters with fail-closed validators),
  ST-SKRIPT-39-02 (Luna/GLM answer-key line with daily token lease and
  correction-session review), ST-SKRIPT-39-03 tasks 03-01/03-02 (both lanes
  on Skriptoteket-owned execution).
- Required predecessors before implementation: TASK-SKRIPT-39-02-03,
  TASK-SKRIPT-39-03-03, TASK-SKRIPT-39-03-04.
- Reuse seeds: `digiexam_ir_contracts.py` item semantics,
  `exam_converter_correction_sessions.py` review/versioning precedent,
  `examnet_qti_package.py` + `examnet_qti_validation.py` export gate;
  `python-docx` is already a dependency. The minimal DOCX writer,
  validation, and file-action seam is a new build per the ST-SKRIPT-21-10
  DOCX-contract slice; Mina filer storage internals are decided during
  implementation.
- Live acceptance stays cited, not re-proven: Sir `TASK-SIRCON-REP-0029`
  and `TASK-SKRIPT-39-01-01` byte parity (`f36a4ae3...`).

## Tasks

1. `TASK-SKRIPT-39-04-01`: DOCX walking skeleton (import, native edit and
   create, save and reopen, export) with a genuine unchanged teacher DOCX.
2. Later slices (unscarffolded until this story is reviewed): digital-PDF
   intake reusing the same native document and review path; deferred
   scanned-PDF behavior once its handling is decided.

## Verification

- One genuine unchanged DOCX fixture converts end to end in-process:
  deterministic extraction with per-item confidence, LLM remainder and
  answer-key proposals, teacher review/edit/create, versioned Mina filer
  save and faithful reopen, and on-demand exports: QTI and PDF through the
  existing fail-closed validators, DOCX through the minimal new writer with
  validation.
- Fixture corpora with per-item confidence assertions and
  teacher-review provenance before export eligibility arrive with breadth
  work; the walking skeleton proves the vertical, not the corpus.
- Backend gates per `AGENTS.md`: lint, typecheck, focused tests. UI/route
  changes get the live functional check recorded in `handoff.md`.

## Decided Contract Terms

| ID | Decided contract term |
| --- | --------------------- |
| S1 | The DOCX walking skeleton proves the full import, edit/create, save/reopen, export vertical before any breadth work. |
| S2 | DOCX implementation begins only after TASK-SKRIPT-39-02-03, TASK-SKRIPT-39-03-03, and TASK-SKRIPT-39-03-04 are done. |
| S3 | Native documents persist versioned in Mina filer; QTI, PDF, and DOCX are on-demand exports only. |
| S4 | LLM output and low-confidence items require teacher-review provenance before export eligibility. |
| S5 | OCR/scanned-PDF handling is deferred out of this story; digital PDF follows as the next slice. |
