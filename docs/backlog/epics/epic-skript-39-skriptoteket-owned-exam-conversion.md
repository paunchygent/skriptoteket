---
type: epic
id: EPIC-SKRIPT-39
title: Skriptoteket-owned exam conversion
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-08-28'
status: active
closeout_review:
  record: inline
  status: not_started
outcome: 'Skriptoteket owns the exam-conversion domain end to end: DigiExam, Word,
  and PDF sources parse into a source-neutral authoring IR and export to the proven
  Exam.net QTI contract, PDF, and DOCX, with Sir Convert-a-Lot retained only as a
  generic heavy-OCR text-extraction service; teachers work in a native editable
  exam workspace with versioned Mina filer documents while PDF, DOCX, and QTI
  remain on-demand exports'
links:
  decisions:
  - ADR-SKRIPT-0090
  - ADR-SKRIPT-0091
backlog_document_profile: contract-derived
---

## Capability Contract

Skriptoteket owns the exam-conversion domain: parsing DigiExam `.dxe`, Word,
and PDF sources into the source-neutral exam authoring IR, advisory LLM
answer-key enrichment behind teacher review, and export to the empirically
proven Exam.net QTI contract, the Exam.net-profile PDF, and DOCX.

- The domain is ported from Sir Convert-a-Lot by incremental strangler:
  lane-by-lane cutover behind the existing Conversion Hub curated-app API,
  with the Sir Convert lane live until each lane's parity is proven, then
  retired lane-by-lane.
- Sir Convert-a-Lot remains the heavy-document and STT service. The exam
  lane's only remaining dependency on it is the generic text-extraction
  contract for scanned or layout-hard PDFs. The mirrored DigiExam schema
  constants and exam-specific client coupling are retired with the cutover.
- Ingestion is deterministic-first: layout, regex, and policy rules produce
  item structure with per-item confidence; the LLM handles only the
  low-confidence remainder and answer-key proposals, always behind the
  teacher-review provenance machine. Unresolved DOCX content remains visible
  for teacher review; no speculative unsupported DigiExam-type handling is
  authorized.
- The first item-type contract is the Exam.net-proven subset: single- and
  multiple-choice, candidate-written gap text, matching, free text, and
  information blocks, with the inline dropdown as a specialized non-default
  family. The full QTI range for straight-to-paper delivery is a later
  capability.
- Answer-key completion is remote-API-first under the daily token lease
  contract decided in sir-convert-a-lot `TASK-SIRCON-08-01-07`; the port
  carries that configuration over. The Hemma Qwen answer-key sidecar is
  retired as a governed cleanup step inside the cutover story.
- Native editable exam workspace: teachers display and edit existing
  questions and create items from scratch. Ingestion is DOCX upload first,
  then digital PDF with embedded text; OCR/scanned PDFs are deferred.
  Deterministic extraction plus LLM parsing, enrichment, and repair run
  behind teacher review. Native persistence is a versioned exam document
  with assets and editing state in Mina filer; PDF, DOCX, and QTI are
  on-demand exports, never native persistence.

Non-goals: the full QTI interaction range, hotspot and video item families,
student-response grading, and LMS integrations. The former exam-creator
non-goal would be narrowed to the workspace slice below by proposed
ADR-SKRIPT-0091.

## Contract Inputs

- The amendment of ADR-SKRIPT-0066 that narrows "no new conversion engines
  inside Skriptoteket" to the new boundary: the exam domain is
  Skriptoteket-owned, heavy OCR and STT stay in Sir Convert-a-Lot behind a
  generic contract. The amendment is required before implementation and lands
  proposed-for-review with this epic.
- Sir Convert-a-Lot prerequisites executing first: `TASK-SIRCON-REP-0029`
  (QTI export repaired to the confirmed Exam.net contract, empirical ledger
  promoted to a governed reference, probe suite as regression fixtures) and
  `TASK-SIRCON-08-01-07` (remote model profiles and the daily token lease).
- Portability evidence: the exam lane imports none of the heavy stack; it
  needs pymupdf, weasyprint, stdlib packaging, and an OpenAI-compatible HTTP
  endpoint, all available or already shipped in Skriptoteket.
- Existing product surface: Conversion Hub Exam Converter lanes
  (`EPIC-SKRIPT-21`, `ST-SKRIPT-21-10`), correction sessions
  (ADR-SKRIPT-0087), public-lane exception (ADR-SKRIPT-0085).
- Retained planning record: sir-convert-a-lot session
  `01a048d5-69f7-7394-93dd-8ff91af608cd`,
  `evidence/planning/TASK-SIRCON-REP-0029/plan.md`.
- 2026-09-05 user-approved workspace scope: native editable exam workspace
  (DOCX first, digital PDF second, OCR deferred; deterministic extraction
  plus LLM parsing/enrichment/repair behind teacher review; versioned Mina
  filer native documents; PDF/DOCX/QTI as on-demand exports), cleanup-first
  sequencing, preserved empirical contract, no new importer research.
  Recorded in ADR-SKRIPT-0091 (`proposed`), ST-SKRIPT-39-04 (`proposed`),
  and TASK-SKRIPT-39-04-01 (`proposed`).

## Stories

Sequenced with explicit dependencies: stories 1-3 complete first; the
workspace skeleton (story 4) follows cleanup; DOCX breadth (story 5) and
digital PDF (story 6) build on the skeleton; QTI import (story 7) is last
and not on the critical path.

1. Walking skeleton: the `.dxe` to authoring-IR to Exam.net QTI-plus-PDF
   bundle runs end to end inside the Skriptoteket backend as a switchable
   lane behind the existing curated-app API, parity-proven against the Sir
   Convert fixtures.
2. Answer-key enrichment port: the structured-LLM harness and teacher-review
   provenance machine move over with the remote-API default and lease budget
   carried from `TASK-SIRCON-08-01-07`.
3. Cutover and retirement: public and authenticated lanes switch, the Sir
   Convert exam lane and mirrored schema constants retire lane-by-lane behind
   parity proof, and the Qwen answer-key sidecar retires as governed cleanup.
4. Native editable exam workspace (`ST-SKRIPT-39-04`, `proposed`): DOCX
   walking skeleton (import, native edit/create, save/reopen, export),
   gated on cleanup tasks 02-03, 03-03, and 03-04 plus ADR-0091/story
   review.
5. Word/DOCX ingestion breadth: deterministic-first parsing corpus with
   per-item confidence assertions and LLM remainder, on the confirmed item
   subset, building on the story-4 skeleton.
6. PDF ingestion: digital PDFs with embedded text parse locally; scanned
   or layout-hard handling is deferred (undecided) while the Sir generic
   extraction capability is preserved as-is without selecting a
   scanned-PDF product route.
7. QTI import: a reader for the proven subset into the authoring IR, making
   export-import-export round-trip a writer regression gate.

## Verification

- Story 1 carries the walking-skeleton proof: one real `.dxe` fixture
  converted in-process with byte-comparable parity against the Sir Convert
  bundle outputs, plus a live functional check of the switchable lane.
- Each cutover lane requires recorded parity proof before the corresponding
  Sir Convert lane retires.
- Ingestion stories verify against fixture corpora with per-item confidence
  assertions; LLM-remainder items require teacher-review provenance before
  export eligibility.
- Frontend or route changes follow the repo rule: live functional check
  recorded in `handoff.md`; backend changes run lint, typecheck, and focused
  tests per `AGENTS.md`.
- The workspace skeleton verifies against one genuine unchanged DOCX
  fixture end to end (import, review/edit/create, versioned save/reopen,
  validator-passing exports); corpus breadth and confidence assertions
  follow with ingestion breadth.

## Epic Verification Plan

| Gate | Verification Result | Evidence | Owner | Follow-up / Exception |
| --- | --- | --- | --- | --- |
| Port the remote answer-key completion line with a daily token lease | verified | `.orchestration/context/sessions/01a04d62-c71c-721c-a43a-76384e182429/evidence/reviews/ST-SKRIPT-39-02/terminal-spec-verification.md` | ST-SKRIPT-39-02 | None |
| Native editable exam workspace DOCX walking skeleton | proposed | ST-SKRIPT-39-04, TASK-SKRIPT-39-04-01, ADR-SKRIPT-0091 | ST-SKRIPT-39-04 | Awaits ADR-0091/story review and cleanup gates (02-03, 03-03, 03-04) |

## Current Implementation Summary

- `ST-SKRIPT-39-02` is done and independently verified. Skriptoteket now owns
  the execution-worker answer-key completion line with Luna low-effort as the
  primary provider, transient-only GLM-5.3-flash failover, a Postgres/UoW
  non-refundable UTC-day token lease, typed exhaustion before provider I/O,
  and authenticated operator balance visibility. Real-DXE live checks cover
  Luna completion, forced failover, and forced exhaustion while preserving
  deterministic conversion and teacher-review semantics.
- 2026-09-05 reconciliation: the user approved the native editable exam
  workspace (DOCX first, digital PDF second, OCR deferred; versioned Mina
  filer native documents; PDF/DOCX/QTI as on-demand exports only) and the
  cleanup-first sequence. Scope is recorded here and in `proposed`
  ADR-SKRIPT-0091, ST-SKRIPT-39-04, and TASK-SKRIPT-39-04-01; nothing is
  claimed complete and no proven acceptance is reopened.

## Decided Contract Terms

| ID  | Decided contract term |
| --- | --------------------- |
| E1  | The exam-conversion domain ports into Skriptoteket as this epic; ADR-SKRIPT-0066 is amended to the new boundary in the same slice. |
| E2  | Migration is incremental strangler with lane-by-lane parity-gated retirement of the Sir Convert exam lane; no big-bang cutover. |
| E3  | The confirmed item contract is the supported types on the Exam.net-proven subset; no unsupported-type handling is authorized (TASK-SKRIPT-39-01-03 canceled). |
| E4  | Ingestion is deterministic-first with LLM only for the low-confidence remainder and answer-key proposals, always behind teacher review. |
| E5  | Heavy OCR and STT remain in Sir Convert-a-Lot behind a generic contract; the exam-specific cross-repo schema surface retires with the cutover. |
| E6  | Teacher authoring (display/edit/create) is in scope only as the native editable exam workspace slice (ST-SKRIPT-39-04 under proposed ADR-SKRIPT-0091, narrowing ADR-SKRIPT-0090's exclusion); QTI import is this epic's final story and not on the critical path. |
| E7  | Answer-key completion is remote-API-first with the 5M-token daily lease contract carried over from TASK-SIRCON-08-01-07; the Qwen answer-key sidecar retires as governed cleanup. |
| E8  | The native editable exam workspace is in scope: teachers display/edit existing questions and create items from scratch. |
| E9  | Native persistence is a versioned exam document with assets and editing state in Mina filer; PDF, DOCX, and QTI are on-demand exports only. |
| E10 | Ingestion order is DOCX upload first, then digital PDF with embedded text; OCR/scanned PDFs are deferred. |
| E11 | DOCX workspace implementation begins only after TASK-SKRIPT-39-02-03, TASK-SKRIPT-39-03-03, and TASK-SKRIPT-39-03-04 are done, preserving generic Sir extraction, OCR, and STT. |
| E12 | The empirical Exam.net contract is preserved as-is; no new importer research and no unsupported DigiExam types are authorized. |
