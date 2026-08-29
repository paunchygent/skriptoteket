---
type: story
id: ST-SKRIPT-39-01
title: Walking skeleton for Skriptoteket-owned exam conversion
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-08-29'
status: active
closeout_review:
  record: inline
  status: not_started
epic: EPIC-SKRIPT-39
acceptance_criteria:
- One real DigiExam .dxe fixture converts end to end inside the Skriptoteket backend
  into an Exam.net QTI package and Exam.net-profile PDF behind the existing curated-app
  API as a switchable lane, with recorded parity proof against the Sir Convert fixture
  outputs and a live functional check
links:
  decisions:
  - ADR-SKRIPT-0090
backlog_document_profile: contract-derived
---

## Slice Contract

Stand the exam-conversion core up inside the Skriptoteket backend and prove
the full chain in-process: parse a real DigiExam `.dxe`, build the source IR
and effective exam, and export the Exam.net-contract QTI package and the
Exam.net-profile PDF, reachable through the existing Conversion Hub
curated-app API as a switchable lane.

- The ported core is the pure-Python exam domain from sir-convert-a-lot at
  its closed-task state (revision `41be61a6`): `.dxe` parser, IR and
  effective-exam contracts, the repaired QTI writer with its
  `assessmentTest` emission and fail-closed preflight validators, and the
  WeasyPrint Exam.net PDF renderer profile. Behavior parity is the
  requirement; Skriptoteket layering (domain/application/infrastructure,
  protocol-first DI, UoW ownership) governs placement.
- The lane switch selects between the existing Sir Convert-backed path and
  the in-process path for the authenticated Exam Converter flow. The Sir
  Convert path stays the default until this story's parity proof is
  recorded; no retirement happens in this slice.
- Answer-key enrichment stays on the existing path in this slice: items
  without machine-usable keys keep their readiness gating; the in-process
  lane must reproduce the same target-readiness behavior for source-keyed
  and overlay-keyed exams. The remote-LLM enrichment port is story 2.
- Out of this slice: Word/PDF ingestion, QTI import, public/anonymous lane
  cutover, correction-session changes, Sir Convert exam-lane retirement,
  and the Qwen sidecar retirement.

## Contract Inputs

- EPIC-SKRIPT-39 capability contract and ADR-SKRIPT-0090 boundary.
- Source of the ported core: sir-convert-a-lot `main` at `41be61a6`
  (TASK-SIRCON-REP-0029 closed; QTI writer live-proven against Exam.net on
  2026-08-29), including the governed empirical import contract
  `REF-SIRCON-GENERAL-exam-net-qti-import-contract-empirical-observations`
  and the probe-derived regression fixtures in
  `tests/sir_convert_a_lot/exam/test_examnet_qti_contract_rules.py`.
- Skriptoteket landing surfaces: `documents.conversion_hub` curated app,
  its authenticated Exam Converter flow, protocol seam
  `src/skriptoteket/protocols/sir_convert_a_lot_v2.py`, and the mirrored
  schema constants in
  `src/skriptoteket/application/curated_apps/sir_convert_contracts.py`.
- Dependencies already present in Skriptoteket: weasyprint, pypdf,
  pdfplumber; pymupdf availability must be confirmed or the extraction
  seams adapted during implementation.
- Retained planning record: sir-convert-a-lot session
  `01a048d5-69f7-7394-93dd-8ff91af608cd`.

## Tasks

1. Walking-skeleton proof (first task, mandated): port the minimal domain
   chain and prove one real `.dxe` fixture end to end in-process with
   byte-comparable parity against the Sir Convert fixture outputs, behind
   the switchable lane, with a live functional check recorded in
   `handoff.md`.
2. Later tasks are decomposed after the skeleton lands: fixture-corpus
   parity breadth, lane-switch operator surface, and readiness-report
   alignment.

## Verification

- Ported regression fixtures (contract rules and package tests) pass inside
  Skriptoteket's test suite.
- Byte-level parity of the QTI package and deterministic comparison of the
  PDF against Sir Convert outputs for the same fixture at `41be61a6`;
  differences must be explained and accepted or eliminated.
- Backend gates per `AGENTS.md`: lint, typecheck, focused tests.
- Live functional check of the switchable lane through the curated-app API,
  recorded in `handoff.md` per repo rule for UI/route changes.

## Decided Contract Terms

| ID  | Decided contract term |
| --- | --------------------- |
| S1  | The walking skeleton is the story's first task and proves the full in-process chain before any breadth work. |
| S2  | The Sir Convert-backed path remains the default until recorded parity proof; the in-process lane ships behind a switch. |
| S3  | The ported core derives from sir-convert-a-lot `41be61a6` and must preserve the live-proven Exam.net contract behavior, including preflight validators. |
| S4  | Answer-key enrichment, ingestion of new source formats, QTI import, retirements, and public-lane cutover are outside this slice. |
