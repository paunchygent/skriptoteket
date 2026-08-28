---
type: epic
id: EPIC-SKRIPT-39
title: Skriptoteket-owned exam conversion
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-08-28'
status: proposed
closeout_review:
  record: inline
  status: not_started
outcome: 'Skriptoteket owns the exam-conversion domain end to end: DigiExam, Word,
  and PDF sources parse into a source-neutral authoring IR and export to the proven
  Exam.net QTI contract, PDF, and DOCX, with Sir Convert-a-Lot retained only as a
  generic heavy-OCR text-extraction service'
links:
  decisions:
  - ADR-SKRIPT-0090
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
  teacher-review provenance machine. Item types outside the proven contract
  degrade to free text with an explicit warning.
- The first item-type contract is the Exam.net-proven subset: single- and
  multiple-choice, candidate-written gap text, matching, free text, and
  information blocks, with the inline dropdown as a specialized non-default
  family. The full QTI range for straight-to-paper delivery is a later
  capability.
- Answer-key completion is remote-API-first under the daily token lease
  contract decided in sir-convert-a-lot `TASK-SIRCON-08-01-07`; the port
  carries that configuration over. The Hemma Qwen answer-key sidecar is
  retired as a governed cleanup step inside the cutover story.

Non-goals: an exam-creator authoring UI (a later epic on the same IR), the
full QTI interaction range, hotspot and video item families,
student-response grading, and LMS integrations.

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

## Stories

Ordered; each later story assumes the earlier ones are done.

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
4. Word/DOCX ingestion: deterministic-first parsing into the authoring IR
   with LLM remainder, on the proven item subset.
5. PDF ingestion: digital PDFs parse locally; scanned or layout-hard PDFs
   route through the Sir Convert generic text-extraction contract.
6. QTI import: a reader for the proven subset into the authoring IR, making
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

## Decided Contract Terms

| ID  | Decided contract term |
| --- | --------------------- |
| E1  | The exam-conversion domain ports into Skriptoteket as this epic; ADR-SKRIPT-0066 is amended to the new boundary in the same slice. |
| E2  | Migration is incremental strangler with lane-by-lane parity-gated retirement of the Sir Convert exam lane; no big-bang cutover. |
| E3  | The first item contract is the Exam.net-proven subset; unknown item types degrade to free text with a warning. |
| E4  | Ingestion is deterministic-first with LLM only for the low-confidence remainder and answer-key proposals, always behind teacher review. |
| E5  | Heavy OCR and STT remain in Sir Convert-a-Lot behind a generic contract; the exam-specific cross-repo schema surface retires with the cutover. |
| E6  | The exam-creator UI is a later epic; QTI import is this epic's final story and not on the critical path. |
| E7  | Answer-key completion is remote-API-first with the 5M-token daily lease contract carried over from TASK-SIRCON-08-01-07; the Qwen answer-key sidecar retires as governed cleanup. |
