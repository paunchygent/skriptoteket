---
type: task
id: TASK-SKRIPT-39-01-01
title: Prove the in-process dxe to Exam.net bundle walking skeleton
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-08-29'
status: done
closeout_review:
  record: inline
  status: approved
  reviewer: independent-reviewer
  decided_at: '2026-08-29'
  approval_protocol: agent-overseer:approved-review-closeout
  approval_evidence: Independent review regenerated the Sir Convert reference from 41be61a6 and reproduced byte-equal QTI-package and PDF parity, verified the full validator set and Exam.net contract obligations on integrated commit 1b7392e6 (merge 704d7fe7, published), and approved on re-review after both requested changes were resolved (upload size caps via read_upload_files; volatile CHECKPOINT.md excluded from the merge) and the authenticated HuleEdu browser-session live check succeeded (job e3be5d9c-b7be-4e7a-9dbc-d7e5dd9aebcb, bundle qti-package.zip sha256 f36a4ae342a4a734a9f8126b694101517a46b7b3751d1b19ece72484a5328698, gateway log proxying to skriptoteket-web:8000), recorded in handoff.md.
task_kind: story
acceptance_criteria:
  - A real DigiExam .dxe fixture converts inside the Skriptoteket backend to an Exam.net QTI package and Exam.net-profile PDF with byte-comparable parity against the Sir Convert outputs at revision 41be61a6, reachable through the authenticated Exam Converter flow behind a lane switch defaulting to the existing Sir Convert path, with the ported contract-rule fixtures passing and a live functional check recorded in handoff.md
story: ST-SKRIPT-39-01
backlog_document_profile: contract-derived
---

## Implementation Contract

Port the minimal exam-conversion chain from sir-convert-a-lot `41be61a6`
into the Skriptoteket backend and prove it end to end.

- Ported modules (behavior-parity, adapted to Skriptoteket layering):
  the `.dxe` parser and DigiExam contracts, source IR and effective-exam
  contracts, the DigiExam-to-QTI adapter, the QTI writer chain
  (contracts, item XML, assessment-test XML, package planner, validators,
  package writer), and the Exam.net PDF renderer profile with its
  WeasyPrint seam. Copy behavior and tests, not service plumbing: job
  lifecycle, target-readiness reporting shape, and artifact naming follow
  Skriptoteket's own application layer.
- Landing placement per repo layering: exam domain logic under a new
  domain/application module set owned by the Conversion Hub curated app;
  infrastructure adapters (WeasyPrint, file handling) in infrastructure;
  protocol seams where the curated-app handlers consume the new lane.
- Lane switch: a configuration-driven selector in the authenticated Exam
  Converter flow choosing Sir Convert-backed or in-process conversion.
  Default stays Sir Convert; the switch is operator-facing configuration,
  not teacher-facing UI.
- Parity proof: for at least one real `.dxe` fixture (mirrored from
  sir-convert-a-lot `inputs/examples/`), the in-process QTI package bytes
  match the Sir Convert package bytes at `41be61a6` (or every difference is
  enumerated and accepted); the PDF is compared deterministically
  (byte-equal where the renderer allows, otherwise structural comparison
  with recorded rationale).
- Port the probe-derived contract-rule regression fixtures so the empirical
  Exam.net contract is enforced inside Skriptoteket's test suite from day
  one.
- Out of scope: answer-key enrichment (existing path unchanged), Word/PDF
  ingestion, QTI import, public-lane changes, any retirement, and any
  cross-repo schema removal.

## Contract Inputs

- ST-SKRIPT-39-01 slice contract; EPIC-SKRIPT-39; ADR-SKRIPT-0090.
- Source revision: sir-convert-a-lot `main` at `41be61a6` — exam domain
  under `scripts/sir_convert_a_lot/domain/` (digiexam\_*, examnet_qti\_*,
  exam_authoring\_\*), infrastructure seams `examnet_qti_package_writer.py`,
  `digiexam_examnet_pdf_renderer.py`, `weasyprint_html_to_pdf.py`,
  `digiexam_pdf_text.py`, and tests under `tests/sir_convert_a_lot/exam/`.
- Governed contract:
  `REF-SIRCON-GENERAL-exam-net-qti-import-contract-empirical-observations`
  (sir-convert-a-lot) — the writer obligations bind the ported code
  unchanged.
- Skriptoteket surfaces: Conversion Hub curated app modules, the
  authenticated Exam Converter handlers, config (`src/skriptoteket/config.py`),
  DI wiring (`src/skriptoteket/di/curated_apps.py`).
- Dependency check: pymupdf is not currently a Skriptoteket dependency;
  the ported lane needs either pymupdf for result-PDF evidence extraction
  or a deferral of that evidence path in this task (source `.dxe` parsing
  needs no PDF library). Prefer deferral over new heavy dependencies in
  the skeleton; record the choice.
- Third-party library facts (WeasyPrint API, pymupdf if adopted) are
  fetched through the sanctioned docs tooling before code changes.

## Core Vertical And Performance

The core vertical is one authenticated Exam Converter request with the lane
switch set to in-process: upload `.dxe`, convert, download the QTI package
and PDF, matching Sir Convert's outputs. Conversion is CPU-cheap
(stdlib + WeasyPrint); no material performance concern beyond keeping the
conversion out of the request thread if Skriptoteket's existing handlers
require async offloading — follow the existing curated-app job pattern.

## Validation

- Ported unit and contract-rule tests pass under Skriptoteket's pytest
  suite; `pdm run lint`, `pdm run typecheck`, and the focused tests per
  `AGENTS.md`.
- Recorded parity artifact: fixture name, both package hashes, and the
  accepted-difference list (empty for byte parity).
- Live functional check of the switchable lane through the running app,
  recorded in `handoff.md`.

## Stop Conditions

- Parity requires behavior the Skriptoteket layering cannot host without
  duplicating Sir Convert service plumbing: stop and return to story
  planning.
- The ported code would need `Any`/`cast`/type-ignores or legacy shims to
  fit: stop; adapt the design instead.
- Scope pressure toward enrichment, ingestion, or retirement: stop; later
  stories own those.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                                              |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| T1  | The skeleton ports behavior and tests from `41be61a6`, not service plumbing; Skriptoteket layering governs placement.                                              |
| T2  | The in-process lane ships behind an operator-facing switch defaulting to the Sir Convert path.                                                                     |
| T3  | Parity is byte-comparable for the QTI package with any accepted differences enumerated; the empirical-contract fixtures run inside Skriptoteket from this task on. |
| T4  | No new heavy dependencies in the skeleton; the result-PDF evidence path may be deferred rather than adopting pymupdf here.                                         |
