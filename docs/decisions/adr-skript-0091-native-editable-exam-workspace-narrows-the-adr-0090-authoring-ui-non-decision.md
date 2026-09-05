---
type: adr
id: ADR-SKRIPT-0091
title: Native editable exam workspace narrows the ADR-0090 authoring-UI non-decision
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-09-05'
status: proposed
deciders:
- user-lead
links:
  governing:
  - EPIC-SKRIPT-39
  - ADR-SKRIPT-0090
---

## Context

The user approved a native editable exam workspace for EPIC-SKRIPT-39:
upload DOCX first, then digital PDF with embedded text, with OCR/scanned
PDFs deferred. Deterministic extraction plus LLM parsing, enrichment, and
repair run behind teacher review; teachers display and edit existing
questions and create items from scratch; versioned native exam documents
with assets and editing state save and reopen in Mina filer; PDF, DOCX, and
QTI are on-demand exports, never native persistence.

This conflicts with two standing authorities: ADR-SKRIPT-0090's
non-decision ("No exam-creator authoring UI is authorized; that is a later
epic") and EPIC-SKRIPT-39's former non-goal ("an exam-creator authoring UI
(a later epic on the same IR)"). Both predate the user approval. This
proposed decision would narrow both to the workspace slice defined below
before workspace implementation begins. Cleanup comes first:
TASK-SKRIPT-39-03-03 (Sir exam integration retirement, `in_progress`) and
TASK-SKRIPT-39-03-04 (Qwen sidecar retirement, `ready`) are unfinished, and
TASK-SKRIPT-39-02-03 (partial answer-key repair, `ready`) is unfinished; the
workspace builds on the lanes they finish. The empirical Exam.net contract
is preserved as-is: the QTI contract was live-proven against Exam.net in
Sir `TASK-SIRCON-REP-0029`, and the PDF is covered by the local structural
assertion and byte-parity evidence in `TASK-SKRIPT-39-01-01`; no new
importer research and no unsupported DigiExam types are authorized
(TASK-SKRIPT-39-01-03 stays canceled).

## Decision

A native editable exam workspace would be authorized inside EPIC-SKRIPT-39
as ST-SKRIPT-39-04, narrowing ADR-SKRIPT-0090's authoring-UI non-decision
and the epic's former exam-creator non-goal to the workspace slice defined
here:

- Teachers display and edit existing questions and create items from scratch
  in the workspace.
- Native persistence is a versioned exam document with assets and editing
  state in Mina filer. PDF, DOCX, and QTI are on-demand exports only and
  never the persistence format.
- Ingestion order is DOCX upload first, then digital PDF with embedded text;
  OCR/scanned PDFs are deferred out of the workspace slice.
- Ingestion is deterministic-first with per-item confidence; the LLM handles
  parsing, enrichment, and repair of the remainder, always behind the
  teacher-review provenance machine before export eligibility.
- The item contract is the confirmed supported types on the Exam.net-proven
  subset (choice, gap text, matching, free text, information blocks); no
  unsupported-type handling is authorized (TASK-SKRIPT-39-01-03 stays
  canceled). Unresolved DOCX content stays teacher-reviewable.
- DOCX workspace implementation begins only after TASK-SKRIPT-39-02-03,
  TASK-SKRIPT-39-03-03, and TASK-SKRIPT-39-03-04 are done, preserving generic
  Sir document extraction, OCR, and STT.

## Non-Decisions

- No change to the Sir generic-extraction boundary: heavy OCR, layout
  models, GPU runtime, and STT stay in Sir Convert-a-Lot.
- No full QTI interaction range, no hotspot or video item families, no
  student-response grading, no LMS integrations.
- Deferred scanned-PDF behavior (hard-fail with guidance versus queue behind
  generic extraction) is not decided here.
- Native document format internals (new versioned doc type versus
  file-plus-sidecar state) are not decided here.
- No new importer research and no unsupported DigiExam or DigiExam-adjacent
  types (including Enkelt-svar-via-portable-QTI) are authorized.

## Consequences

- EPIC-SKRIPT-39 records the workspace scope and sequencing terms; ST-SKRIPT-39-04
  and TASK-SKRIPT-39-04-01 carry the DOCX walking skeleton.
- This ADR is `proposed`: workspace implementation waits for its review plus
  the ST-SKRIPT-39-04 review and the cleanup gates above.
- Retirement of the Qwen sidecar is governed by TASK-SKRIPT-39-03-04 and of
  the Sir exam lane by TASK-SKRIPT-39-03-03; no live deployment state is
  asserted here.
