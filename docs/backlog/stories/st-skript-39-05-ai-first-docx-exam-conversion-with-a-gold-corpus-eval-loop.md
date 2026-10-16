---
type: story
id: ST-SKRIPT-39-05
title: AI-first DOCX exam conversion with a gold-corpus eval loop
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-10-10'
status: ready
closeout_review:
  record: inline
  status: not_started
epic: EPIC-SKRIPT-39
acceptance_criteria:
- Each eval run aims for every item of every corpus exam to match its hand-checked
  gold item, as a best-effort target; anything that cannot be converted becomes a
  review item holding its source text. Full corpus reruns stay rare because of their
  cost.
links:
  decisions: []
backlog_document_profile: contract-derived
---

## Slice Contract

A teacher uploads a DOCX exam in any reasonable layout and gets a native
exam document whose items are ready to edit and export, without deciding
what the app can resolve itself. The rule extractor of ST-SKRIPT-39-04
converts only 3 of the 8 corpus exams; this story replaces rule-first
extraction with an AI-first converter and proves it against a hand-checked
gold corpus.

- **The parser only prepares chunks.** Code segments the DOCX into solid
  chunks (headings, instructions, prompts, options with their line breaks,
  tables, facit text, points). It does not decide what an item asks.
- **AI produces contract-ready items.** The Decisions API and the Responses
  API work in combination with strict JSON and no tools. Calls are batched
  across items, never one call per item. Code validates every item against
  the native document contract; only failing items are sent again, at most
  three rounds. The target is success on the first call.
- **Rules stay minimal and general.** Rules know input types, never one
  exam's wording or labels. A rule is added only when the eval loop shows a
  need.
- **Nothing is lost.** Input that still fails after the retries becomes a
  free-text item holding its source text, marked for review with a Swedish
  note that names why. Export stays blocked until the teacher fixes it.
- **No failure is invisible.** Every failure in the conversion path is
  observed with its exact reason: each admission rejection per item and
  round, provider errors, invalid or refused output, retry exhaustion,
  review-item fallback and job failure. Each is a structured log event with
  the job id and a reason code, and is persisted with the job outcome so it
  can be read without log access.
- **Conversion runs in the background.** Upload returns at once, the
  document shows a converting status and opens when done. The uploaded DOCX
  is kept until the job finishes.
- **Item shapes.** The four current kinds plus a new matching kind. A word
  bank becomes gap text where each gap accepts its own facit word. Any other
  shape becomes a review item.
- **The teacher is asked only about what the app cannot resolve.**
  Check-passing interpretation of the teacher's own facit is applied and
  export-eligible, marked "Tolkad av AI" with undo. Answer keys the AI
  invents without a facit keep the teacher check. The app adds obvious
  misspellings of facit answers within a code-enforced edit distance, never
  synonyms. The gap popover gets "Visa som text".

Out of scope: digital PDF (story 6), QTI import (story 7), exporter
convergence (story 8), and carrying answer-key proposals across saves
(TASK-SKRIPT-39-04-04). This story supersedes TASK-SKRIPT-39-04-03.

## Contract Inputs

- EPIC-SKRIPT-39 (story 5), ST-SKRIPT-39-04, ADR-SKRIPT-0091.
- Corpus: `tests/fixtures/exam_conversion/docx_corpus/` (eight exams with
  facit, `144d6333`) and the current-importer probe in retained session
  `01a1263d-5783-74c7-823d-9b4475c85915`.
- Import handler `application/curated_apps/handlers/exam_workspace_documents.py`
  (169-215); rule extractor `domain/curated_apps/exam_workspace/docx_extraction.py`.
- Native contract and export blockers
  `domain/curated_apps/exam_workspace/native_exam_document.py`; QTI mapping
  `examnet_qti_export.py`; planner and fail-closed validator
  `domain/curated_apps/exam_conversion/examnet_qti_package.py` and
  `examnet_qti_validation.py` (matching rules already present).
- LLM lane: `infrastructure/llm/openai/answer_key_structured_provider.py`,
  daily token lease `infrastructure/repositories/exam_answer_key_token_leases.py`,
  job pattern `exam_answer_key_enrichment_jobs`.
- OpenAI Decisions API (public beta, `gpt-6-luna`) and Responses structured
  outputs; fetch current docs through Context7 before implementation.
- HuleEduOS `examnet-qti-import` empirical observations (2026-08-28):
  matchInteraction directedPair import is proven.

## Tasks

Planned order; each task is scaffolded and contracted before work starts.

1. `TASK-SKRIPT-39-05-01` walking skeleton: one corpus exam runs upload -> stored DOCX ->
   background job -> chunker -> batched AI build -> validation -> review-item
   fallback -> workspace opens -> QTI export passes validation.
2. `TASK-SKRIPT-39-05-02` gold corpus and eval loop: a gold file per corpus exam confirmed by the
   user, and an eval runner that reports every item mismatch.
3. Corpus breadth: Decisions classification, retries for failing items
   only, and general rules added only where the eval loop shows a need,
   aiming for every corpus item to meet the conversion principles against its
   gold as a best-effort target.
4. Matching kind: native model, editor, and QTI export (delivered in
   `TASK-SKRIPT-39-05-03`, D1, D7, D8).
5. `TASK-SKRIPT-39-05-10` (done 2026-10-14) teacher surface: AI glyph with undo on interpreted
   keys, checked AI-invented keys, automatic misspellings, and
   "Visa som text".
6. `TASK-SKRIPT-39-05-09` (done 2026-10-14): label-first per-question retry;
   DOCX pictures as positioned exam assets in review and converted items, the
   editor, QTI, PDF and DOCX; a prompt sentence keeps low-27 field-label phrases
   as text (D44); the marking guide stays out of QTI after the Exam.net probe
   (D31). Exam.net imports the pictures.
7. `TASK-SKRIPT-39-05-07` (done 2026-10-13): export is blocked only by missing values and unbuilt
   questions; printed "(N p)" markers become points; possible parsing issues
   fire only where wording is lost (user decisions 2026-10-13).
8. `TASK-SKRIPT-39-05-08` (done 2026-10-14): imported questions carry no
   title; printed group headings open the group instruction or the question
   body; one gap_fill/free_text definition; Exam.net imports the result.
9. `TASK-SKRIPT-39-05-11` (done 2026-10-15): the labeling feasibility report
   scores its converter baseline from the committed v14 batch recordings.
10. `TASK-SKRIPT-39-05-13` (done 2026-10-16): the DOCX build prompt is a
   shared core plus one section per item kind; a chunk the grouping lists as
   a question's facit is its answer key unless the item holds it; batches hold
   16 question families (307/316 items match gold vs 298/316 at 1).
11. `TASK-SKRIPT-39-05-14`: exam header lines become document metadata
   (course hint, printed totals checked against item points) and never exam
   text; numbered or pointed question headings open their question or parent.

## Verification

- Eval loop: each run aims for every item of every corpus exam to meet the
  conversion principles (TASK-SKRIPT-39-05-03) against its gold file, as a
  best-effort target; full corpus reruns stay rare because of their cost.
- Unit tests for chunking, contract validation, the retry bound, and the
  review-item fallback.
- QTI export of every converted corpus exam passes the fail-closed
  validators.
- Backend and frontend gates per `AGENTS.md`.
- Agent-driven browser walk on Hemma staging: upload, wait for conversion,
  review, undo one AI interpretation, save, export QTI.

## Decided Contract Terms

| ID  | Decided contract term |
| --- | --------------------- |
| A1 | The AI-first converter is this story under EPIC-SKRIPT-39; TASK-SKRIPT-39-04-03 is superseded with a pointer and ST-SKRIPT-39-04 stays as delivered (user decision 2026-10-10). |
| A2 | The parser only segments; AI produces contract-ready items using the Decisions and Responses APIs in combination, strict JSON, no tools, batched across items; only failing items are retried, at most three rounds; first-call success is the target (user direction 2026-10-10). |
| A3 | Rules know input types, never one exam's wording; rules are added only where the eval loop shows a need (user direction 2026-10-10; full corpus reruns stay rare per A15). |
| A4 | Unconvertible input becomes a free-text review item holding its source text with a Swedish note; export stays blocked until fixed (user decision 2026-10-10). |
| A5 | Conversion runs as a background job with a visible status; the uploaded DOCX is kept until the job finishes (user decision 2026-10-10). |
| A6 | A matching kind is added; a word bank becomes gap text where each gap accepts its own facit word; other shapes become review items (user decision 2026-10-10). |
| A7 | The pass bar is a user-confirmed gold file per corpus exam; each run aims for every item to meet the conversion principles against it, as a best-effort target. Gold is one correct conversion, not the only one (user decision 2026-10-10, refined 2026-10-11 and 2026-10-16 per A15). |
| A8 | Check-passing AI interpretation of the teacher's facit is applied and export-eligible as "Tolkad av AI" with undo (user decision 2026-10-10, carried from 39-04-03 F10). |
| A9 | AI-invented answer keys without a facit keep the teacher check before export (user decision 2026-10-10, carried from F11). |
| A10 | The app adds obvious misspellings of facit answers within a code-enforced edit distance, never synonyms (user decision 2026-10-10, carried from F6). |
| A11 | The gap popover gets "Visa som text" (user decision 2026-10-10, carried from F4). |
| A12 | The app resolves what AI and code can reasonably resolve; the teacher is asked only about the rest (user direction 2026-10-10). |
| A13 | Every failure in the conversion path is observed with its exact reason, as a structured log event with the job id and a reason code and persisted with the job outcome; no failure is silent (user decision 2026-10-10, after the live staging walk of TASK-SKRIPT-39-05-01 failed without rejection reasons). |
| A14 | The AI call carries the producer contract: a strict structured-output schema for the native item shapes plus the conversion rules in the instructions. The consumer parses that guaranteed output and runs only the native document contract and export validation; it does not re-verify the producer with forensic source-binding rules (user decision 2026-10-10, "producer contract, not consumer validation"). |
| A15 | The gold-corpus bar is a best-effort target, not a closure gate on every item of every run; full corpus reruns stay rare because a 314-item run is costly. The earlier every-item-every-run wording was stricter than the GrillMe agreement (user decision 2026-10-16). |
